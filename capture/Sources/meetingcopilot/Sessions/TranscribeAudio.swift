import ArgumentParser
import Foundation
@preconcurrency import AVFoundation

/// Recovery tool: decode an audio snapshot locally, without session hooks,
/// deliveries, or touching the running recorder.
struct TranscribeAudio: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "transcribe-audio",
        abstract: "Transcribe an audio snapshot locally to timed JSON (no delivery)."
    )
    @Argument var audio: String
    @Argument var output: String
    @Flag(help: "Recover voice slots from the audio; names are not inferred.")
    var voices = false

    func run() throws {
        let audioURL = URL(fileURLWithPath: audio)
        let outputURL = URL(fileURLWithPath: output)
        struct Span: Encodable, Sendable {
            let start: Double
            let end: Double
            let text: String
            var voice_id: String? = nil
        }
        let recoverVoices = voices
        let semaphore = DispatchSemaphore(value: 0)
        nonisolated(unsafe) var result: Result<[Span], Error>?
        Task {
            do {
                let engine = ParakeetEngine()
                try await engine.prepare()
                let segments = try await engine.transcribe(audioURL)
                await engine.release()
                var spans = segments.map { Span(start: $0.start, end: $0.end, text: $0.text) }
                if recoverVoices {
                    guard let diarizer = await RemoteSpeakerDiarizer.load() else {
                        throw ValidationError("Voice model unavailable; refusing to invent speakers")
                    }
                    let file = try AVAudioFile(forReading: audioURL)
                    let capacity = AVAudioFrameCount(file.processingFormat.sampleRate / 2)
                    var observations: [(Double, Int)] = []
                    while file.framePosition < file.length {
                        let position = Double(file.framePosition) / file.processingFormat.sampleRate
                        guard let buffer = AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: capacity) else { break }
                        try file.read(into: buffer, frameCount: capacity)
                        if let voice = try diarizer.process(buffer) { observations.append((position, voice)) }
                    }
                    for index in spans.indices {
                        let matching = observations.filter { $0.0 >= spans[index].start && $0.0 < spans[index].end }
                        let counts = Dictionary(grouping: matching, by: { $0.1 }).mapValues { $0.count }
                        if let voice = counts.max(by: { $0.value < $1.value })?.key {
                            spans[index].voice_id = "remote-\(voice + 1)"
                        }
                    }
                }
                result = .success(spans)
            } catch { result = .failure(error) }
            semaphore.signal()
        }
        semaphore.wait()
        let spans = try result!.get()
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(spans).write(to: outputURL, options: .atomic)
    }
}
