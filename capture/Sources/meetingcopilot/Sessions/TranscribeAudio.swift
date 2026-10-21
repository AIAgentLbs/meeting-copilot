import ArgumentParser
import FluidAudio
import Foundation

/// Recovery tool: decode an audio snapshot with the person's speech choice
/// (or a one-run override), without session hooks, deliveries, or touching
/// the running recorder.
struct TranscribeAudio: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "transcribe-audio",
        abstract: "Transcribe an audio snapshot to timed JSON with the chosen speech model (no delivery)."
    )
    @Argument var audio: String
    @Argument var output: String
    @Flag(help: "Recover voice slots with the speaker model on this Mac; names are not inferred.")
    var voices = false
    @OptionGroup var speech: SpeechChoiceOptions

    func run() throws {
        ModelHub.offlineMode = true
        let resolution = try speech.choice().map(STTRuntime.check) ?? Config.speechRecognition()
        guard case .ready(let choice) = resolution else {
            throw ValidationError(resolution.reason)
        }
        var speaker: LocalSpeakerModel?
        if voices {
            guard let present = LocalSpeakerModel.installed.first else {
                throw ValidationError("No speaker model on this Mac; refusing to invent speakers")
            }
            speaker = present
        }
        struct Span: Encodable, Sendable {
            let start: Double
            let end: Double
            let text: String
            var voice_id: String? = nil
        }
        let audioURL = URL(fileURLWithPath: audio)
        let spans = try runBlocking { [speaker] in
            let engine = try STTRuntime.engine(for: choice)
            try await engine.prepare()
            let segments = try await engine.transcribe(audioURL)
            await engine.release()
            var spans = segments.map { Span(start: $0.start, end: $0.end, text: $0.text) }
            if let speaker {
                let observations = try RemoteSpeakerDiarizer.load(speaker).observations(in: audioURL)
                for index in spans.indices {
                    spans[index].voice_id = RemoteSpeakerDiarizer.voice(
                        from: spans[index].start, to: spans[index].end, in: observations
                    ).map { "remote-\($0 + 1)" }
                }
            }
            return spans
        }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(spans).write(to: URL(fileURLWithPath: output), options: .atomic)
    }
}
