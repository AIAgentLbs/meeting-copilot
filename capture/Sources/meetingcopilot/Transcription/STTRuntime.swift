import FluidAudio
import Foundation

/// Turns the stored speech choice into something that runs, or into the
/// reason it cannot run yet. Everything here is checked against this Mac
/// without the network: the files on disk, the keys, the platform.
enum STTRuntime {
    struct Failure: TranscriptionFailure, CustomStringConvertible {
        let description: String
        var isPermanent: Bool { false }
        init(_ description: String) { self.description = description }
    }

    static func resolve(stored: [String: Any]?) -> STTResolution {
        let (choice, missing) = STTChoice.parse(stored)
        guard let choice else {
            let detail = stored == nil ? "" : " (missing: \(missing.joined(separator: ", ")))"
            return .needsChoice(STTChoice.needsChoiceMessage + detail)
        }
        return check(choice)
    }

    /// Whether a complete choice can run on this Mac now. The same check
    /// guards a one-run override, so `process --again --model X` cannot run
    /// something the stored choice could not.
    static func check(_ choice: STTChoice) -> STTResolution {
        switch choice.engine {
        case STTChoice.localEngine:
            guard Platform.supportsLocalModels else {
                return .unavailable("local speech models need a Mac with Apple Silicon")
            }
            guard let model = LocalSTTModel.parse(choice.model) else {
                return .unavailable("\(choice.model) is not a model the FluidAudio adapter can run")
            }
            guard model.isDownloaded else {
                return .unavailable("\(choice.model) is not downloaded; download it in Getting started")
            }
            if let problem = languageProblem(choice.language, for: model) {
                return .unavailable(problem)
            }
        case "openai", "assemblyai":
            guard key(for: choice.engine) != nil else {
                return .unavailable("no \(choice.engine) API key; add one in Getting started")
            }
        default:
            return .unavailable("\(choice.engine) is not a speech engine this app can run")
        }
        return .ready(choice)
    }

    /// The language a local model was asked for, checked against what the
    /// model itself says it takes: a downloaded Nemotron ship's prompt
    /// dictionary, or the cached model card for Parakeet. Nothing is checked
    /// when nothing is known: the Getting started card validated it on save.
    static func languageProblem(_ language: String, for model: LocalSTTModel) -> String? {
        switch model {
        case .nemotron:
            guard let prompts = model.localNemotronPrompts else { return nil }
            guard prompts.contains(language) else {
                return language == STTChoice.autoLanguage
                    ? "\(model.id) cannot detect the language; choose one in Getting started"
                    : "\(model.id) does not list the language \(language)"
            }
            return nil
        case .parakeet:
            guard let languages = STTCatalog.cachedCardLanguages(model) else { return nil }
            if language == STTChoice.autoLanguage {
                return languages.count > 1
                    ? nil : "\(model.id) cannot detect the language; choose one in Getting started"
            }
            return languages.contains(language) ? nil : "\(model.id) does not list the language \(language)"
        }
    }

    static func key(for engine: String) -> String? {
        switch engine {
        case "openai": return Config.openAIKey()
        case "assemblyai": return Config.assemblyAIKey()
        default: return nil
        }
    }

    /// The engine a ready choice names. Throws only for a choice `check`
    /// would have refused.
    static func engine(for choice: STTChoice) throws -> TranscriptionEngine {
        switch choice.engine {
        case STTChoice.localEngine:
            switch LocalSTTModel.parse(choice.model) {
            case .parakeet(let version):
                return ParakeetEngine(version: version, language: choice.language)
            case .nemotron(let ship):
                return NemotronFileEngine(model: .nemotron(ship: ship), language: choice.language)
            case nil:
                throw Failure("\(choice.model) is not a model the FluidAudio adapter can run")
            }
        case "openai":
            return try OpenAITranscriptionEngine(model: choice.model, language: choice.language)
        case "assemblyai":
            return try AssemblyAIEngine(model: choice.model, language: choice.language)
        default:
            throw Failure("\(choice.engine) is not a speech engine this app can run")
        }
    }
}
