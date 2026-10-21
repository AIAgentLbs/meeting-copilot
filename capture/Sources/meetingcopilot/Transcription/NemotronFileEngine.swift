import FluidAudio
import Foundation

/// A Nemotron streaming ship used for a final transcript: the recorded track
/// is fed through the same streaming decoder the live transcript uses, so one
/// chosen model serves both. The ship must already be downloaded.
actor NemotronFileEngine: TranscriptionEngine {
    nonisolated let name = STTChoice.localEngine
    nonisolated let model: String
    nonisolated let input: TranscriptionInput = .perTrack

    private let directory: URL
    private let language: String
    private var shared: SharedNemotronMultilingualModels?

    init(model: LocalSTTModel, language: String) {
        self.model = model.id
        directory = model.directory
        self.language = language
    }

    func prepare() async throws {
        guard shared == nil else { return }
        guard LocalSTTModel.nemotronVariantReady(at: directory) else {
            throw TranscriptionDeferred(
                kind: .unavailable, reason: "\(model) is not downloaded; download it in Getting started")
        }
        shared = try await StreamingNemotronMultilingualAsrManager.preloadShared(from: directory)
    }

    func transcribe(_ audio: URL) async throws -> [TranscriptSegment] {
        guard let shared else { throw ParakeetEngine.EngineError.notPrepared }
        let samples: [Float]
        do {
            samples = try AudioConverter().resampleAudioFile(audio)
        } catch {
            throw ParakeetEngine.EngineError.unreadableAudio(audio, error)
        }
        guard !samples.isEmpty else { throw ParakeetEngine.EngineError.unreadableAudio(audio, nil) }

        // A fresh decoder per track: the streaming state must not carry from
        // the mic track into the system one.
        let manager = StreamingNemotronMultilingualAsrManager()
        try await manager.loadFromShared(shared)
        await manager.setLanguage(language)
        defer { Task { await manager.cleanup() } }
        let step = 16_000 * 30
        var offset = 0
        while offset < samples.count {
            let end = min(offset + step, samples.count)
            _ = try await manager.process(samples: Array(samples[offset..<end]))
            offset = end
        }
        let (text, timings) = try await manager.finishWithTokenTimings()
        let words = buildWordTimings(from: timings)
        guard !words.isEmpty else {
            let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty
                ? [] : [TranscriptSegment(start: 0, end: Double(samples.count) / 16_000, text: trimmed)]
        }
        return ParakeetEngine.segments(from: words)
    }

    func release() async {
        shared = nil
    }
}
