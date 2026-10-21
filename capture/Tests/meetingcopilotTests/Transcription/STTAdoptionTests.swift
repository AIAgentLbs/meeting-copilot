import AVFoundation
import Foundation
import Testing

@testable import meetingcopilot

/// The one speech choice: where it comes from (the person, the settings it
/// replaced, the one model the installer downloaded), that nothing else ever
/// fills it in, and that a session waiting for it loses nothing.
struct STTAdoptionTests {
    private static let v3 = LocalSTTModel.parakeet(.v3)
    private static let v2 = LocalSTTModel.parakeet(.v2)
    private static let ship = LocalSTTModel.nemotron(ship: "multilingual/1120ms")

    private static func migrated(
        _ json: [String: Any], installed: [LocalSTTModel] = [],
        language: (LocalSTTModel) -> String? = { _ in nil }
    ) -> [String: Any]? {
        var json = json
        STTChoice.migrateLegacy(&json, installed: installed, language: language)
        return STTChoice.stored(in: json)
    }

    // MARK: - the installer's model

    @Test("The one installed model becomes the choice, with the language it implies")
    func oneInstalledModelIsAdopted() {
        let choice = Self.migrated([:], installed: [Self.v3], language: { _ in "auto" })
        #expect(choice as? [String: String]
            == ["engine": "fluidaudio", "model": Self.v3.id, "language": "auto"])
        #expect(STTChoice.parse(choice).0 == STTChoice(engine: "fluidaudio", model: Self.v3.id, language: "auto"))
    }

    @Test("Zero or several installed models leave the choice to the person")
    func zeroOrSeveralAreNotAdopted() {
        #expect(Self.migrated([:], installed: [], language: { _ in "auto" }) == nil)
        #expect(Self.migrated([:], installed: [Self.v3, Self.ship], language: { _ in "auto" }) == nil)
    }

    @Test("An installed model whose language is not known yet is not half-adopted")
    func unknownLanguageWaits() {
        #expect(Self.migrated([:], installed: [Self.v3]) == nil)
    }

    @Test("A stored choice, even an unfinished one, is never replaced")
    func storedChoiceWins() {
        let stored: [String: Any] = ["stt": ["choice": ["engine": "openai"]]]
        let choice = Self.migrated(stored, installed: [Self.v3], language: { _ in "auto" })
        #expect(choice as? [String: String] == ["engine": "openai"])
    }

    @Test("Adoption writes through the locked config writer and keeps other keys")
    func adoptionWritesTheFile() throws {
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("meetontrack-stt-adopt-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }
        let file = dir.appendingPathComponent("config.json")
        try Data(#"{"summary": {"enabled": true}}"#.utf8).write(to: file)

        Config.migrateLegacySpeechChoice(file: file, installed: [Self.ship], language: { _ in "auto" })
        guard case .object(let json) = ConfigFile.read(file) else { Issue.record("unreadable"); return }
        #expect((json["summary"] as? [String: Any])?["enabled"] as? Bool == true)
        #expect(STTChoice.stored(in: json) as? [String: String]
            == ["engine": "fluidaudio", "model": Self.ship.id, "language": "auto"])

        // Once there is a choice, a second model appearing changes nothing.
        Config.migrateLegacySpeechChoice(file: file, installed: [Self.v2], language: { _ in "en" })
        guard case .object(let again) = ConfigFile.read(file) else { Issue.record("unreadable"); return }
        #expect((STTChoice.stored(in: again)?["model"] as? String) == Self.ship.id)
    }

    // MARK: - the settings it replaced

    @Test("Each legacy engine carries over only what the file says")
    func legacyShapes() {
        let parakeet = Self.migrated(
            ["transcription": ["engine": "parakeet", "model": "v3"]], language: { _ in "auto" })
        #expect(parakeet as? [String: String] == ["engine": "fluidaudio", "model": Self.v3.id, "language": "auto"])

        let openai = Self.migrated(
            ["transcription": ["engine": "openai", "openai": ["model": "some-model"], "language": "ru"]])
        #expect(openai as? [String: String] == ["engine": "openai", "model": "some-model", "language": "ru"])

        let assembly = Self.migrated(["transcription": ["engine": "assemblyai"]])
        #expect(assembly as? [String: String] == ["engine": "assemblyai"])

        // `auto` was a code default, not a choice: it carries nothing over,
        // and the installer's model decides instead when there is one.
        #expect(Self.migrated(["transcription": ["engine": "auto", "model": "v3"]]) == nil)
        let adopted = Self.migrated(
            ["transcription": ["engine": "auto"]], installed: [Self.v2], language: { _ in "en" })
        #expect(adopted?["model"] as? String == Self.v2.id)
    }

    @Test("No default fills a missing key")
    func missingKeysAreNeedsChoice() {
        let (choice, missing) = STTChoice.parse(["engine": "fluidaudio", "model": Self.v3.id])
        #expect(choice == nil)
        #expect(missing == ["language"])
        guard case .needsChoice = STTRuntime.resolve(stored: nil) else {
            Issue.record("no choice must be needs_choice"); return
        }
        #expect(STTChoice.parse(nil).missing == STTChoice.keys)
    }

    @Test("A model implies auto when it detects languages, its one language, or nothing")
    func impliedLanguage() {
        #expect(STTChoice.impliedLanguage(languages: ["en", "ru"], autoDetect: true) == "auto")
        #expect(STTChoice.impliedLanguage(languages: ["en"], autoDetect: false) == "en")
        #expect(STTChoice.impliedLanguage(languages: ["en", "ru"], autoDetect: false) == nil)
        #expect(STTChoice.impliedLanguage(languages: nil, autoDetect: nil) == nil)

        let options: [String: Any] = ["engines": [
            ["id": "openai", "models": [["id": "x", "languages": ["en"], "auto_detect": NSNull()]]],
            ["id": "fluidaudio", "models": [
                ["id": Self.v3.id, "languages": ["en", "ru"], "auto_detect": true],
                ["id": Self.v2.id, "languages": ["en"], "auto_detect": false],
            ]],
        ]]
        let implied = STTCatalog.impliedLanguages(options)
        #expect(implied[Self.v3.id] == "auto")
        #expect(implied[Self.v2.id] == "en")
        #expect(implied["x"] == nil)
    }

    @Test("A one-run choice needs all three keys or none")
    func overrideNeedsAll() throws {
        #expect(try STTChoice.override(engine: nil, model: nil, language: nil) == nil)
        #expect(throws: STTChoice.OverrideError.self) {
            try STTChoice.override(engine: "openai", model: "m", language: nil)
        }
        #expect(try STTChoice.override(engine: "openai", model: "m", language: "auto")
            == STTChoice(engine: "openai", model: "m", language: "auto"))
    }

    // MARK: - Python and Swift speak the same words

    @Test("The shared vocabulary file matches the Swift side")
    func vocabularyParity() throws {
        let file = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("copilot/web/stt_vocabulary.json")
        let shared = try #require(
            try JSONSerialization.jsonObject(with: Data(contentsOf: file)) as? [String: Any])
        #expect(shared["options_contract"] as? String == STTCatalog.contract)
        #expect(shared["check_contract"] as? String == STTCheck.contract)
        #expect(shared["config_path"] as? [String] == STTChoice.configPath)
        #expect(shared["choice_keys"] as? [String] == STTChoice.keys.sorted())
        #expect(Set(shared["engines"] as? [String] ?? []) == STTChoice.engines)
        #expect(Set(shared["states"] as? [String] ?? [])
            == Set([STTResolution.ready(STTChoice(engine: "", model: "", language: "")),
                    .needsChoice(""), .unavailable("")].map(\.state)))
        #expect(shared["auto_language"] as? String == STTChoice.autoLanguage)
        #expect(shared["deferred_key"] as? String == TranscriptionDeferred.key)
        #expect(SessionState.Key.transcriptionDeferred == TranscriptionDeferred.key)
        #expect(Set(shared["deferred_kinds"] as? [String] ?? [])
            == Set(TranscriptionDeferred.Kind.allCases.map(\.rawValue)))
    }

    // MARK: - waiting costs nothing

    @Test("A session waiting for a choice keeps its attempts and its audio")
    func deferredSessionKeepsAttempts() async throws {
        let dir = try Self.session()
        defer { try? FileManager.default.removeItem(at: dir.deletingLastPathComponent()) }
        let coordinator = TranscriptionCoordinator(
            onStop: { nil }, resolve: { .needsChoice(STTChoice.needsChoiceMessage) })
        for _ in 0..<4 {
            await #expect(throws: TranscriptionDeferred.self) { try await coordinator.transcribeNow(dir) }
        }
        let meta = try #require(
            try JSONSerialization.jsonObject(with: Data(contentsOf: dir.appendingPathComponent("meta.json")))
                as? [String: Any])
        #expect((meta[TranscriptionDeferred.key] as? [String: Any])?["kind"] as? String == "needs_choice")
        #expect(meta[SessionState.Key.transcriptionAttempts] == nil)
        #expect(meta[SessionState.Key.transcriptionFailed] == nil)
        #expect(FileManager.default.fileExists(atPath: dir.appendingPathComponent("mic.caf").path))
        #expect(FileManager.default.fileExists(atPath: dir.appendingPathComponent("system.caf").path))
        #expect(TranscriptionCoordinator.pendingSessions(in: dir.deletingLastPathComponent())
            .map { $0.resolvingSymlinksInPath().path }.contains(dir.resolvingSymlinksInPath().path))
        #expect(!SessionClaim.isHeld(dir))
    }

    private static func session() throws -> URL {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meetontrack-deferred-\(UUID().uuidString)", isDirectory: true)
        let dir = root.appendingPathComponent("2026-10-21 10-00", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let format = AVAudioFormat(standardFormatWithSampleRate: 16_000, channels: 1)!
        for name in ["mic.caf", "system.caf"] {
            let file = try AVAudioFile(forWriting: dir.appendingPathComponent(name), settings: format.settings)
            let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: 16_000)!
            buffer.frameLength = 16_000
            try file.write(from: buffer)
        }
        try JSONSerialization.data(withJSONObject: [
            "files": ["mic": "mic.caf", "system": "system.caf"],
            "start_offset_ms": ["mic": 0, "system": 0],
            "duration_seconds": 1,
        ]).write(to: dir.appendingPathComponent("meta.json"))
        return dir
    }
}
