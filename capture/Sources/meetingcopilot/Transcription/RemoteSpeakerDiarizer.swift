@preconcurrency import AVFoundation
import FluidAudio
import Foundation

/// Separates the mixed far-end system-audio track into stable, meeting-local
/// voice slots. Zoom/Meet names are resolved later from visible active-speaker
/// frames; this layer deliberately identifies voices, not people.
final class RemoteSpeakerDiarizer: @unchecked Sendable {
    private let diarizer: LSEENDDiarizer
    private let converter = AudioConverter(sampleRate: 8_000)
    private var acceptedVoice: Int?
    private var pendingVoice: Int?
    private var pendingCount = 0

    private init(diarizer: LSEENDDiarizer) {
        self.diarizer = diarizer
    }

    /// Model failure must never take down transcription. DIHARD3 is the broad
    /// mixed-condition model (up to ten voice slots); a 500 ms step keeps CPU
    /// use reasonable on an 8 GB M2 while remaining live enough for the UI.
    static func load() async -> RemoteSpeakerDiarizer? {
        do {
            let diarizer = try await LSEENDDiarizer(
                variant: .dihard3,
                stepSize: .step500ms,
                timelineConfig: DiarizerTimelineConfig(
                    numSpeakers: 10,
                    frameDurationSeconds: 0.1,
                    onsetThreshold: 0.42,
                    offsetThreshold: 0.36,
                    onsetPadFrames: 1,
                    offsetPadFrames: 1,
                    minFramesOn: 2,
                    minFramesOff: 2,
                    activityType: .sigmoids,
                    maxStoredFrames: 36_000,
                    storeSegments: true
                )
            )
            return RemoteSpeakerDiarizer(diarizer: diarizer)
        } catch {
            FileHandle.standardError.write(Data(
                "remote speaker diarization unavailable: \(error)\n".utf8
            ))
            return nil
        }
    }

    /// Returns a zero-based voice slot. A changed slot must win two model
    /// updates in a row, preventing a single noisy half-second from splitting
    /// a transcript paragraph. The first confident voice is accepted at once.
    func process(_ buffer: AVAudioPCMBuffer) throws -> Int? {
        let samples = try converter.resampleBuffer(buffer)
        guard !samples.isEmpty,
              let update = try diarizer.process(samples: samples, sourceSampleRate: 8_000),
              let observed = Self.dominantVoice(
                predictions: update.chunkResult.finalizedPredictions,
                speakerCount: diarizer.numSpeakers ?? 10
              )
        else { return nil }

        guard let acceptedVoice else {
            self.acceptedVoice = observed
            pendingVoice = nil
            pendingCount = 0
            return observed
        }
        guard observed != acceptedVoice else {
            pendingVoice = nil
            pendingCount = 0
            return acceptedVoice
        }

        if pendingVoice == observed {
            pendingCount += 1
        } else {
            pendingVoice = observed
            pendingCount = 1
        }
        guard pendingCount >= 2 else { return acceptedVoice }
        self.acceptedVoice = observed
        pendingVoice = nil
        pendingCount = 0
        return observed
    }

    /// Picks the strongest voice over the newest 500 ms, rejecting silence
    /// and ambiguous overlap. Kept internal so it can be verified without a
    /// model download in unit tests.
    static func dominantVoice(
        predictions: [Float],
        speakerCount: Int,
        minimumProbability: Float = 0.42,
        minimumMargin: Float = 0.06
    ) -> Int? {
        guard speakerCount > 0,
              !predictions.isEmpty,
              predictions.count.isMultiple(of: speakerCount)
        else { return nil }
        let frameCount = predictions.count / speakerCount
        let firstFrame = max(0, frameCount - 5)
        let divisor = Float(frameCount - firstFrame)
        var means = Array(repeating: Float.zero, count: speakerCount)
        for frame in firstFrame..<frameCount {
            for speaker in 0..<speakerCount {
                means[speaker] += predictions[frame * speakerCount + speaker] / divisor
            }
        }
        let ranked = means.enumerated().sorted { $0.element > $1.element }
        guard let best = ranked.first, best.element >= minimumProbability else { return nil }
        let runnerUp = ranked.dropFirst().first?.element ?? 0
        guard best.element - runnerUp >= minimumMargin else { return nil }
        return best.offset
    }
}
