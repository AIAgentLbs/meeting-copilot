import Foundation

/// The person's one speech recognition choice, exactly as stored under
/// `stt.choice` in the shared config: the engine adapter, the model id as the
/// engine's discovery lists it, and the language (`auto` only for a model that
/// detects it). Speakers are labelled by channel (microphone: you, call
/// audio: others) unless the model identifies speakers itself; there is no
/// speaker setting (owner decision 2026-10-21).
///
/// No code default ever fills one in. It comes from the person: chosen in
/// Getting started, carried over from the settings that came before it, or
/// the one model the installer downloaded (owner decision 2026-10-21). A
/// choice that is not all there does not run: sessions wait, deferred, until
/// it is finished (docs/specs/2026-10-20-no-hardcoded-models.md, Phase 3).
struct STTChoice: Equatable, Sendable {
    let engine: String
    let model: String
    let language: String

    static let configPath = ["stt", "choice"]
    static let keys = ["engine", "language", "model"]
    static let engines: Set<String> = ["fluidaudio", "assemblyai", "openai"]
    static let localEngine = "fluidaudio"
    static let autoLanguage = "auto"

    static let needsChoiceMessage = "choose speech recognition in Getting started"

    var isLocal: Bool { engine == Self.localEngine }

    /// A file-name-safe key for a cloud response cache, so a cached answer is
    /// only reused for the same model and language.
    static func cacheKey(model: String, language: String) -> String {
        "\(model)-\(language)".unicodeScalars.map {
            CharacterSet.alphanumerics.contains($0) || $0 == "-" || $0 == "." ? String($0) : "_"
        }.joined()
    }

    var json: [String: String] {
        ["engine": engine, "model": model, "language": language]
    }

    /// The stored object, complete or not, for display and for deciding
    /// whether the migration still has anything to do.
    static func stored(in config: [String: Any]?) -> [String: Any]? {
        (config?["stt"] as? [String: Any])?["choice"] as? [String: Any]
    }

    /// A complete choice, or nil with the keys that are missing.
    static func parse(_ stored: [String: Any]?) -> (STTChoice?, missing: [String]) {
        guard let stored else { return (nil, keys) }
        func text(_ key: String) -> String? {
            (stored[key] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines)
        }
        var missing: [String] = []
        for key in keys where (text(key) ?? "").isEmpty {
            missing.append(key)
        }
        guard missing.isEmpty else { return (nil, missing) }
        return (STTChoice(engine: text("engine")!, model: text("model")!, language: text("language")!), [])
    }

    /// A one-run choice from command-line arguments: all three or none.
    static func override(engine: String?, model: String?, language: String?) throws -> STTChoice? {
        if engine == nil, model == nil, language == nil { return nil }
        guard let engine, let model, let language,
              !engine.isEmpty, !model.isEmpty, !language.isEmpty
        else {
            throw OverrideError()
        }
        return STTChoice(engine: engine, model: model, language: language)
    }

    struct OverrideError: Error, CustomStringConvertible {
        var description: String {
            "a one-run speech choice needs all of --engine, --model and --language"
        }
    }

    /// The language a local model implies by itself: `auto` when it detects
    /// the language, its only language when it has one, otherwise nil (the
    /// person picks). Facts come from the model, never from a list here.
    static func impliedLanguage(languages: [String]?, autoDetect: Bool?) -> String? {
        if autoDetect == true { return autoLanguage }
        if let languages, languages.count == 1 { return languages[0] }
        return nil
    }

    // MARK: - the settings this replaced

    /// Fill `stt.choice` while there is none yet, from what the person
    /// already decided:
    ///
    /// 1. the transcription settings that came before it. Only keys written
    ///    in the file count, never a value that used to be a code default:
    ///    `auto` (or no engine) carries nothing over. A language comes from
    ///    the file, or from the local model itself (`impliedLanguage`).
    /// 2. otherwise the one local model the installer downloaded (`installed`:
    ///    the speech models in our own model folders). Zero or several leave
    ///    the choice to the person. Several is a real choice; guessing one
    ///    would be a code default.
    ///
    /// `language` answers `impliedLanguage` for a local model, or nil while
    /// its facts are not known on this Mac yet (the choice then waits).
    static func migrateLegacy(
        _ json: inout [String: Any],
        installed: [LocalSTTModel],
        language: (LocalSTTModel) -> String?
    ) {
        guard stored(in: json) == nil else { return }
        let transcription = json["transcription"] as? [String: Any] ?? [:]
        func text(_ section: [String: Any]?, _ key: String) -> String? {
            guard let value = (section?[key] as? String)?
                .trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty
            else { return nil }
            return value
        }
        var choice: [String: Any] = [:]
        switch text(transcription, "engine") {
        case "parakeet":
            choice["engine"] = localEngine
            if let version = text(transcription, "model"),
               let model = LocalSTTModel.legacyParakeet(version) {
                choice["model"] = model.id
            }
        case "openai":
            choice["engine"] = "openai"
            choice["model"] = text(transcription["openai"] as? [String: Any], "model")
        case "assemblyai":
            choice["engine"] = "assemblyai"
            choice["model"] = text(transcription["assemblyai"] as? [String: Any], "speech_model")
        default:
            guard installed.count == 1, let only = installed.first, let implied = language(only) else { return }
            choice = ["engine": localEngine, "model": only.id, "language": implied]
        }
        if choice["language"] == nil {
            choice["language"] = text(transcription, "language")
                ?? (choice["model"] as? String).flatMap(LocalSTTModel.parse).flatMap(language)
        }
        var stt = json["stt"] as? [String: Any] ?? [:]
        stt["choice"] = choice
        json["stt"] = stt
    }
}

/// What the stored choice adds up to on this Mac right now.
enum STTResolution: Equatable, Sendable {
    case ready(STTChoice)
    case needsChoice(String)
    case unavailable(String)

    var state: String {
        switch self {
        case .ready: return "ready"
        case .needsChoice: return "needs_choice"
        case .unavailable: return "unavailable"
        }
    }

    var reason: String {
        switch self {
        case .ready: return ""
        case .needsChoice(let reason), .unavailable(let reason): return reason
        }
    }
}

/// A session that cannot be transcribed yet for a reason that will pass: no
/// finished choice, a model not downloaded, an engine that cannot run, or no
/// network. It is not a failure and costs none of the session's attempts.
struct TranscriptionDeferred: Error, CustomStringConvertible {
    enum Kind: String, CaseIterable { case needsChoice = "needs_choice", unavailable, network }

    static let key = "transcription_deferred"

    let kind: Kind
    let reason: String

    var description: String { "deferred (\(kind.rawValue)): \(reason)" }

    init(kind: Kind, reason: String) {
        self.kind = kind
        self.reason = reason
    }

    init?(_ resolution: STTResolution) {
        switch resolution {
        case .ready: return nil
        case .needsChoice(let reason): self.init(kind: .needsChoice, reason: reason)
        case .unavailable(let reason): self.init(kind: .unavailable, reason: reason)
        }
    }

    var metadata: [String: String] {
        ["kind": kind.rawValue, "reason": reason, "at": ISO8601DateFormatter().string(from: Date())]
    }
}

extension Config {
    /// The stored speech choice after the one-time migration, resolved
    /// against what this Mac has.
    static func speechRecognition() -> STTResolution {
        migrateLegacySpeechChoice()
        return STTRuntime.resolve(stored: STTChoice.stored(in: current()))
    }

    /// Run the one-time migration through the locked writer when there is
    /// anything to migrate. A file that can't be parsed is left alone.
    /// `language` defaults to what this Mac knows offline; discovery passes
    /// what it just read from the model hosts.
    static func migrateLegacySpeechChoice(
        file: URL = Config.path,
        installed: @autoclosure () -> [LocalSTTModel] = LocalSTTModel.installed,
        language: (LocalSTTModel) -> String? = { $0.offlineImpliedLanguage }
    ) {
        let json: [String: Any]
        switch ConfigFile.read(file) {
        case .object(let object): json = object
        case .missing: json = [:]
        default: return
        }
        // The common case, read on every resolution: nothing to do, and no
        // need to look at the model folders.
        guard STTChoice.stored(in: json) == nil else { return }
        let installed = installed()
        var probe = json
        STTChoice.migrateLegacy(&probe, installed: installed, language: language)
        guard !NSDictionary(dictionary: probe).isEqual(to: json) else { return }
        do {
            let written = try ConfigFile.update(file) {
                STTChoice.migrateLegacy(&$0, installed: installed, language: language)
            }
            if written { NotificationCenter.default.post(name: didChange, object: nil) }
        } catch {
            FileHandle.standardError.write(Data(
                "couldn't migrate the old transcription settings: \(error)\n".utf8))
        }
    }
}
