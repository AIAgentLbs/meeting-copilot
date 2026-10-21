import Foundation

/// The person's one choice of AI, exactly as stored in `ai.choice` of the
/// shared config, where the Python web app's Getting started page writes it.
/// Every AI task uses it: summaries and speaker names here, live analysis,
/// translation, screenshots and rewrites in the web app (owner decision
/// 2026-10-21). The provider adapter, the model id as that provider lists it,
/// the effort level ("" when the model has none) and the speed tier (""
/// when none is offered, "standard" for the default tier, anything else a
/// provider tier id).
///
/// Nothing here ever fills one in. A choice that is not all there does not
/// run, and the person is asked: owner rule 2026-10-20, see
/// docs/specs/2026-10-20-no-hardcoded-models.md.
struct AIChoice: Equatable {
    let provider: String
    let model: String
    let effort: String
    let speed: String

    static let needsChoiceMessage = "needs choice: choose AI in Getting started"

    /// Providers this app can run. Antigravity is known but refused: its
    /// print mode reports `permission_mode: always-proceed`, so read-only and
    /// no-tools cannot be enforced for a transcript.
    static let runnable: Set<String> = ["codex", "claude", "ollama"]
    static let antigravityRefusal =
        "cannot enforce read-only/no-tools: permission_mode always-proceed"

    static func resolve(in config: [String: Any]?) -> AIResolution {
        guard
            let stored = stored(in: config),
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

    /// `ai.choice`, or, until the web app has written it, what it will carry
    /// over from the per-task choices that came before (same rule as Python
    /// `migrated_choice`): the complete ones if they are all the same, or the
    /// only complete one; when several differ, `live_analysis` if complete,
    /// else nothing. The old summary backends can only give a partial choice,
    /// which does not run either way, so they are not read here.
    static func stored(in config: [String: Any]?) -> [String: Any]? {
        let ai = config?["ai"] as? [String: Any]
        if let choice = ai?["choice"] { return choice as? [String: Any] }
        let purposes = ai?["purposes"] as? [String: Any] ?? [:]
        let complete = purposes.values.compactMap { $0 as? [String: Any] }.filter(isComplete)
        guard let first = complete.first else { return nil }
        if complete.allSatisfy({ NSDictionary(dictionary: $0).isEqual(to: first) }) { return first }
        guard let live = purposes["live_analysis"] as? [String: Any], isComplete(live) else { return nil }
        return live
    }

    private static func isComplete(_ choice: [String: Any]) -> Bool {
        let values = ["provider", "model", "effort", "speed"].map { (choice[$0] as? String)?.trimmed }
        return !values.contains(nil) && values[0] != "" && values[1] != ""
    }

    // MARK: - the settings this replaced

    /// A legacy `summary.backend: "none"` meant "no summaries": it becomes
    /// `summary.enabled: false` and the backend key is dropped, so turning
    /// summaries on later works. The other legacy backends feed `ai.choice`
    /// once; the web app, which owns `ai`, carries them over.
    static func migrateLegacy(_ json: inout [String: Any]) {
        guard var summary = json["summary"] as? [String: Any],
              (summary["backend"] as? String)?.trimmed == "none" else { return }
        summary["backend"] = nil
        summary["enabled"] = false
        json["summary"] = summary
    }
}

enum AIResolution: Equatable {
    case ready(AIChoice)
    case needsChoice
    case unavailable(String)
}

extension Config {
    /// Run the one-time migration through the locked writer, if there is
    /// anything to migrate. A file that can't be parsed is left alone: the
    /// task then reports the file's problem rather than running.
    static func migrateLegacyAIChoices(file: URL = Config.path) {
        guard case .object(let json) = ConfigFile.read(file) else { return }
        var probe = json
        AIChoice.migrateLegacy(&probe)
        guard !NSDictionary(dictionary: probe).isEqual(to: json) else { return }
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
