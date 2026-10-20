import Foundation

/// The tasks in this app that ask a language model something. Their raw
/// values are the keys under `ai.purposes` in the shared config, where the
/// Python web app's Getting started page stores the person's choice.
enum AIPurpose: String, CaseIterable {
    case summary
    case speakerNames = "speaker_names"
}

/// One person's choice of AI for one purpose, exactly as stored: the provider
/// adapter, the model id as that provider lists it, the effort level ("" when
/// the model has none) and the speed tier ("" when none is offered,
/// "standard" for the default tier, anything else a provider tier id).
///
/// Nothing here ever fills one in. A choice that is not all there does not
/// run, and the person is asked — owner rule 2026-10-20, see
/// docs/specs/2026-10-20-no-hardcoded-models.md.
struct AIChoice: Equatable {
    let provider: String
    let model: String
    let effort: String
    let speed: String

    static let needsChoiceMessage = "needs choice — choose AI in Getting started"

    /// Providers this app can run. Antigravity is known but refused: its
    /// print mode reports `permission_mode: always-proceed`, so read-only and
    /// no-tools cannot be enforced for a transcript.
    static let runnable: Set<String> = ["codex", "claude", "ollama"]
    static let antigravityRefusal =
        "cannot enforce read-only/no-tools: permission_mode always-proceed"

    static func resolve(_ purpose: AIPurpose, in config: [String: Any]?) -> AIResolution {
        let purposes = (config?["ai"] as? [String: Any])?["purposes"] as? [String: Any]
        guard
            let stored = purposes?[purpose.rawValue] as? [String: Any],
            let provider = (stored["provider"] as? String)?.trimmed,
            let model = (stored["model"] as? String)?.trimmed,
            let effort = (stored["effort"] as? String)?.trimmed,
            let speed = (stored["speed"] as? String)?.trimmed,
            !provider.isEmpty, !model.isEmpty
        else { return .needsChoice }

        if provider == "antigravity" { return .unavailable(antigravityRefusal) }
        guard runnable.contains(provider) else {
            return .unavailable("\(provider) is not a provider this app can run")
        }
        return .ready(AIChoice(provider: provider, model: model, effort: effort, speed: speed))
    }

    // MARK: - the settings this replaced

    /// Fill `ai.purposes` once from the settings that came before it, when a
    /// purpose has no choice yet and the file itself names a backend for it.
    ///
    /// Only what is written in the file counts — never a value that used to
    /// be a code default — and only the backends that map onto a provider
    /// this app runs (`claude-cli`, `codex-cli`, `ollama`). The model comes
    /// along when the file names one for that backend. Effort and speed are
    /// left out on purpose, so the person is asked for them.
    static func migrateLegacy(_ json: inout [String: Any]) {
        var ai = json["ai"] as? [String: Any] ?? [:]
        var purposes = ai["purposes"] as? [String: Any] ?? [:]
        let summary = json["summary"] as? [String: Any] ?? [:]
        let naming = json["speaker_names"] as? [String: Any] ?? [:]

        func text(_ section: [String: Any], _ key: String) -> String? {
            guard let value = (section[key] as? String)?.trimmed, !value.isEmpty else { return nil }
            return value
        }
        func provider(_ section: [String: Any]) -> String? {
            ["claude-cli": "claude", "codex-cli": "codex", "ollama": "ollama"][
                text(section, "backend") ?? ""]
        }
        /// The model key each legacy backend read. Naming had no codex or
        /// ollama model of its own and used the summary's.
        func model(for provider: String, _ section: [String: Any]) -> String? {
            switch provider {
            case "claude": return text(section, "model") ?? text(summary, "model")
            case "codex": return text(summary, "openai_model")
            default: return text(summary, "ollama_model")
            }
        }

        var changed = false
        for (purpose, section) in [(AIPurpose.summary, summary), (.speakerNames, naming)]
        where purposes[purpose.rawValue] == nil {
            guard let provider = provider(section) else { continue }
            var choice: [String: Any] = ["provider": provider]
            choice["model"] = model(for: provider, section)
            purposes[purpose.rawValue] = choice
            changed = true
        }
        guard changed else { return }
        ai["purposes"] = purposes
        json["ai"] = ai
    }
}

enum AIResolution: Equatable {
    case ready(AIChoice)
    case needsChoice
    case unavailable(String)
}

extension Config {
    /// Run the one-time migration through the locked writer, if there is
    /// anything to migrate. A file that can't be parsed is left alone — the
    /// purpose then reports the file's problem rather than running.
    static func migrateLegacyAIChoices(file: URL = Config.path) {
        guard case .object(let json) = ConfigFile.read(file) else { return }
        var probe = json
        AIChoice.migrateLegacy(&probe)
        guard probe["ai"] != nil, !NSDictionary(dictionary: probe).isEqual(to: json) else { return }
        do {
            let written = try ConfigFile.update(file) { AIChoice.migrateLegacy(&$0) }
            if written { NotificationCenter.default.post(name: didChange, object: nil) }
        } catch {
            FileHandle.standardError.write(Data(
                "couldn't migrate the old summary settings: \(error)\n".utf8))
        }
    }
}

private extension String {
    var trimmed: String { trimmingCharacters(in: .whitespacesAndNewlines) }
}
