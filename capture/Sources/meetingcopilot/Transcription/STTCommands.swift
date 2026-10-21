@preconcurrency import AVFoundation
import ArgumentParser
import FluidAudio
import Foundation

/// `--engine --model --language`: a speech choice for one run, all three or none.
struct SpeechChoiceOptions: ParsableArguments {
    @Option(help: "Speech engine for this run only (with --model and --language).")
    var engine: String?
    @Option(help: "Speech model id as `stt-options` lists it.")
    var model: String?
    @Option(help: "Language code, or auto when the model detects it.")
    var language: String?

    func choice() throws -> STTChoice? {
        do {
            return try STTChoice.override(engine: engine, model: model, language: language)
        } catch {
            throw ValidationError("\(error)")
        }
    }
}

private func printJSON(_ object: Any) {
    guard let data = try? JSONSerialization.data(
        withJSONObject: object, options: [.sortedKeys, .withoutEscapingSlashes])
    else { return }
    FileHandle.standardOutput.write(data + Data("\n".utf8))
}

/// The speech engines, models and speaker models this Mac can use, as
/// `meetontrack.stt-options/1` JSON.
struct STTOptions: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "stt-options",
        abstract: "List speech recognition engines and models as JSON.")

    @Flag(help: "Print JSON (the only output format).") var json = false
    @Flag(help: "Ask the model hosts again instead of using the day-old cache.") var refresh = false

    func run() throws {
        ModelHub.offlineMode = true
        let refresh = refresh
        let options = try runBlocking { await STTCatalog.options(refresh: refresh).sendable }
        printJSON(options.value)
    }
}

/// The one place speech models are downloaded, on an explicit request from
/// Getting started. Progress is one JSON object per line.
struct STTDownload: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "stt-download",
        abstract: "Download a speech model, printing JSON progress.")

    @Option(help: "Speech model id as `stt-options` lists it.") var model: String
    @Flag(help: "Print JSON lines (the only output format).") var json = false

    func run() throws {
        ModelHub.offlineMode = false
        let item = "model", id = model
        guard let local = LocalSTTModel.parse(model) else {
            printJSON(["event": "error", "item": item, "id": id,
                       "message": "\(model) is not a model FluidAudio can download"])
            throw ExitCode(1)
        }
        do {
                try runBlocking {
                    try await local.download { progress in
                        var event: [String: Any] = [
                            "event": "progress", "item": item, "id": id,
                            "fraction": progress.fractionCompleted,
                        ]
                        switch progress.phase {
                        case .listing: event["phase"] = "listing"
                        case .downloading(let done, let total):
                            event["phase"] = "downloading"
                            event["completed_files"] = done
                            event["total_files"] = total
                        case .compiling: event["phase"] = "compiling"
                        }
                        printJSON(event)
                    }
                }
                printJSON(["event": "done", "item": item, "id": id])
                printJSON(try runBlocking { await Self.speakerModel().sendable }.value)
        } catch {
            printJSON(["event": "error", "item": item, "id": id, "message": "\(error)"])
            throw ExitCode(1)
        }
        printJSON(["event": "finished", "ok": true])
    }

    /// The speaker model rides along with a local speech model. A failure
    /// never fails the download: speakers are then labelled by channel. A
    /// `note` event, which the web server ignores, says what happened.
    static func speakerModel(
        _ speaker: LocalSpeakerModel = .companion,
        fetch: (LocalSpeakerModel) async throws -> Void = { try await $0.download() }
    ) async -> [String: Any] {
        var note: [String: Any] = ["event": "note", "item": "speaker_model", "id": speaker.id]
        if speaker.isDownloaded {
            note["state"] = "present"
            return note
        }
        do {
            try await fetch(speaker)
            note["state"] = "downloaded"
        } catch {
            note["state"] = "failed"
            note["message"] = "speaker model not fetched (\(error)); speakers are labelled by channel"
        }
        return note
    }
}

/// Run the choice once on a second of generated audio: proof that the
/// model loads (local) or that the provider accepts the model and key
/// (cloud). Only an explicit Check runs it.
struct STTCheck: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "stt-check",
        abstract: "Check a speech choice on one second of audio, printing JSON.")

    static let contract = "meetontrack.stt-check/1"

    @OptionGroup var speech: SpeechChoiceOptions
    @Flag(help: "Print JSON (the only output format).") var json = false

    func run() throws {
        ModelHub.offlineMode = true
        let override = try speech.choice()
        let result = try runBlocking { await Self.check(override).sendable }
        printJSON(result.value)
        if (result.value["ok"] as? Bool) != true { throw ExitCode(1) }
    }

    static func check(_ override: STTChoice?) async -> [String: Any] {
        var steps: [[String: Any]] = []
        var out: [String: Any] = ["contract": contract, "ok": false, "model_used": "", "error": ""]
        func step(_ name: String, _ ok: Bool, _ detail: String) {
            steps.append(["name": name, "ok": ok, "detail": detail])
        }
        defer { out["steps"] = steps }

        let resolution = override.map(STTRuntime.check) ?? Config.speechRecognition()
        out["choice"] = override?.json ?? STTChoice.stored(in: Config.current()) ?? NSNull()
        guard case .ready(let choice) = resolution else {
            step("choice", false, resolution.reason)
            out["error"] = resolution.reason
            out["steps"] = steps
            return out
        }
        step("choice", true, "\(STTCatalog.engineName(choice.engine)) \(STTCatalog.displayName(choice.model, in: .english)), "
             + "language \(choice.language)")

        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("meetontrack-stt-check-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: dir) }
        do {
            try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            let audio = try oneSecond(in: dir)
            let engine = try STTRuntime.engine(for: choice)
            try await engine.prepare()
            step("load", true, engine.model)
            do {
                let segments = try await engine.transcribe(audio)
                step("transcribe", true, "\(segments.count) segment(s) from one second of silence")
            } catch let failure as TranscriptionFailure where failure.isPermanent {
                // "No speech in this audio" is the right answer to silence:
                // the provider took the model and the key.
                step("transcribe", true, "\(failure)")
            }
            let used = await engine.modelUsed()
            out["model_used"] = used
            out["model_used_name"] = STTCatalog.displayName(used, in: .english)
            await engine.release()
            out["ok"] = true
        } catch {
            step(steps.count == 1 ? "load" : "transcribe", false, "\(error)")
            out["error"] = "\(error)"
        }
        out["steps"] = steps
        return out
    }

    /// One second of two-channel silence, the shape every engine accepts.
    static func oneSecond(in dir: URL) throws -> URL {
        let url = dir.appendingPathComponent("check.m4a")
        let format = AVAudioFormat(standardFormatWithSampleRate: 16_000, channels: 2)!
        let file = try AVAudioFile(forWriting: url, settings: [
            AVFormatIDKey: kAudioFormatMPEG4AAC, AVSampleRateKey: 16_000, AVNumberOfChannelsKey: 2,
        ])
        let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: 16_000)!
        buffer.frameLength = 16_000
        try file.write(from: buffer)
        return url
    }
}

/// `[String: Any]` across a `runBlocking` boundary. The dictionary is built
/// and read on one logical path; nothing shares it.
struct SendableJSON: @unchecked Sendable { let value: [String: Any] }

extension Dictionary where Key == String, Value == Any {
    var sendable: SendableJSON { SendableJSON(value: self) }
}
