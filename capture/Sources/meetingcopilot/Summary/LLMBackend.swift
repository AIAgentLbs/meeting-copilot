import Darwin
import Foundation

/// The one way of asking a language model a question for a purpose: the
/// provider, model, effort and speed the person chose in Getting started
/// (`ai.purposes.<purpose>` in the shared config).
///
/// There is no chain and no `auto`. A purpose without a complete choice does
/// not run and says so; a choice that cannot run says why. Which model is
/// strong enough for a summary is the person's decision, made from the list
/// the installed provider offers, not this file's.
///
/// Every provider gets the transcript in the prompt, on stdin or in the
/// request body, and no tools: CLIs run in a fresh empty folder with their
/// tools, shell, MCP and web search turned off.
struct LLMBackend {
    /// The provider adapter: `codex`, `claude` or `ollama`.
    let name: String
    /// The model id that was asked for.
    let model: String
    /// (system prompt, user prompt) → the answer and the model that gave it.
    let call: (String, String) async throws -> LLMReply
    /// The most prompt characters one call may carry, when the provider has a
    /// limit worth sizing to (Ollama's context window); nil means no such limit.
    var inputLimit: () async throws -> Int? = { nil }

    /// The backend for a purpose, from the person's config. Runs the one-time
    /// migration of the old summary settings first.
    static func resolve(_ purpose: AIPurpose) -> LLMBackendResolution {
        Config.migrateLegacyAIChoices()
        if let problem = Config.loadProblem() { return .unavailable(problem) }
        return resolve(purpose, config: Config.current(), tool: cliPath)
    }

    static func resolve(
        _ purpose: AIPurpose,
        config: [String: Any]?,
        tool: (String) -> String?,
        environment: [String: String] = ProcessInfo.processInfo.environment
    ) -> LLMBackendResolution {
        switch AIChoice.resolve(purpose, in: config) {
        case .needsChoice: return .needsChoice
        case .unavailable(let reason): return .unavailable(reason)
        case .ready(let choice):
            switch choice.provider {
            case "codex":
                guard let path = tool("codex") else { return .unavailable("the codex CLI is not installed") }
                return .ready(codex(path: path, choice: choice))
            case "claude":
                guard let path = tool("claude") else { return .unavailable("the claude CLI is not installed") }
                guard ["", "standard", "fastMode"].contains(choice.speed) else {
                    return .unavailable("claude offers no speed tier \(choice.speed)")
                }
                return .ready(claude(path: path, choice: choice))
            default:
                return .ready(ollama(choice: choice, url: ollamaChatURL(environment: environment)))
            }
        }
    }

    // MARK: - Codex

    static func codexArguments(_ choice: AIChoice, workdir: String, packageRoot: String) -> [String] {
        var args = ["--ask-for-approval", "never", "-m", choice.model]
        if !choice.effort.isEmpty {
            args += ["-c", "model_reasoning_effort=\(toml(choice.effort))"]
        }
        if !choice.speed.isEmpty, choice.speed != "standard" {
            args += ["-c", "service_tier=\(toml(choice.speed))"]
        }
        // Read-only on nothing but an empty folder and Codex's own package,
        // which its sandbox helper has to be able to read to start at all.
        args += [
            "-c", #"default_permissions="meetontrack""#,
            "-c", "permissions.meetontrack.filesystem={\":minimal\"=\"read\","
                + "\(toml(workdir))=\"read\",\(toml(packageRoot))=\"read\"}",
            "exec", "--ignore-user-config", "--skip-git-repo-check", "--ephemeral",
            "--disable", "shell_tool", "--disable", "unified_exec", "--disable", "multi_agent",
            "--disable", "enable_mcp_apps", "--disable", "skill_search",
            "--disable", "skill_mcp_dependency_install", "--disable", "tool_suggest",
            "-c", #"web_search="disabled""#, "-c", "project_doc_max_bytes=0",
            "-c", "skills.include_instructions=false",
            "-C", workdir, "--json", "-",
        ]
        return args
    }

    /// The text of the last finished agent message in `codex exec --json`.
    static func codexAnswer(_ stdout: Data) -> String? {
        var answer: String?
        for event in jsonLines(stdout) where event["type"] as? String == "item.completed" {
            guard let item = event["item"] as? [String: Any],
                  item["type"] as? String == "agent_message",
                  let text = item["text"] as? String
            else { continue }
            answer = text
        }
        guard let answer, !answer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        else { return nil }
        return answer
    }

    private static func codex(path: String, choice: AIChoice) -> LLMBackend {
        LLMBackend(name: "codex", model: choice.model) { system, prompt in
            try await inEmptyFolder { workdir in
                let stdout = try await run(
                    executable: path,
                    arguments: codexArguments(
                        choice, workdir: workdir.path, packageRoot: packageRoot(of: path)),
                    input: "\(system)\n\n\(prompt)",
                    timeout: 1800,
                    currentDirectory: workdir)
                guard let text = codexAnswer(Data(stdout.utf8)) else {
                    throw LLMError.emptyResponse("codex")
                }
                // `codex exec --json` does not report the model; the one asked
                // for is the one that ran.
                return LLMReply(text: text, model: choice.model)
            }
        }
    }

    /// dirname(dirname(realpath(codex))): the folder Codex is installed in.
    static func packageRoot(of executable: String) -> String {
        URL(fileURLWithPath: realPath(executable))
            .deletingLastPathComponent().deletingLastPathComponent().path
    }

    /// realpath(3). Foundation's `resolvingSymlinksInPath` deliberately keeps
    /// `/var` rather than `/private/var`, which is not what a sandbox sees.
    static func realPath(_ path: String) -> String {
        guard let pointer = realpath(path, nil) else { return path }
        defer { free(pointer) }
        return String(cString: pointer)
    }

    // MARK: - Claude

    static func claudeArguments(_ choice: AIChoice) -> [String] {
        var args = [
            "-p", "--output-format", "stream-json", "--verbose",
            "--setting-sources", "", "--strict-mcp-config",
            "--model", choice.model,
        ]
        if !choice.effort.isEmpty { args += ["--effort", choice.effort] }
        if choice.speed == "fastMode" { args += ["--settings", #"{"fastMode":true}"#] }
        return args + ["--tools", "", "--no-session-persistence"]
    }

    /// The answer from the `result` event and the model from `system/init`,
    /// which is the one that actually ran.
    static func claudeReply(_ stdout: Data, requested: String) throws -> LLMReply {
        var model = requested
        var text: String?
        var failed = false
        for event in jsonLines(stdout) {
            switch event["type"] as? String {
            case "system" where event["subtype"] as? String == "init":
                if let reported = event["model"] as? String, !reported.isEmpty { model = reported }
            case "result":
                text = event["result"] as? String
                failed = event["is_error"] as? Bool ?? false
            default:
                continue
            }
        }
        if failed { throw LLMError.exit(0, text ?? "claude reported an error") }
        guard let text, !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw LLMError.emptyResponse("claude")
        }
        return LLMReply(text: text, model: model)
    }

    private static func claude(path: String, choice: AIChoice) -> LLMBackend {
        LLMBackend(name: "claude", model: choice.model) { system, prompt in
            try await inEmptyFolder { workdir in
                let stdout = try await run(
                    executable: path,
                    arguments: claudeArguments(choice),
                    input: "\(system)\n\n\(prompt)",
                    timeout: 1800,
                    currentDirectory: workdir)
                return try claudeReply(Data(stdout.utf8), requested: choice.model)
            }
        }
    }

    // MARK: - Ollama

    static func ollamaChatURL(environment: [String: String]) -> URL {
        var host = environment["OLLAMA_HOST"]?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if host.isEmpty { host = "http://127.0.0.1:11434" }
        while host.hasSuffix("/") { host.removeLast() }
        if !host.contains("://") { host = "http://" + host }
        return URL(string: host + "/api/chat") ?? URL(string: "http://127.0.0.1:11434/api/chat")!
    }

    /// Room kept for the answer inside Ollama's context, in tokens.
    /// ponytail: one fixed allowance; size it per purpose if answers get cut.
    static let ollamaReplyTokens = 4096

    /// The context length the model reports in `/api/show`
    /// (`model_info["<general.architecture>.context_length"]`), or nil.
    static func ollamaContextLength(_ show: [String: Any]) -> Int? {
        guard let info = show["model_info"] as? [String: Any],
              let arch = info["general.architecture"] as? String,
              let length = (info["\(arch).context_length"] as? NSNumber)?.intValue, length > 0
        else { return nil }
        return length
    }

    /// Prompt characters that fit a context of `contextLength` tokens.
    /// ponytail: counts one character as at least one token, which holds for
    /// the Latin and Cyrillic text of a transcript; use a tokenizer if CJK
    /// transcripts get truncated.
    static func ollamaInputLimit(contextLength: Int) -> Int {
        max(0, contextLength - ollamaReplyTokens)
    }

    /// The /api/chat body. `num_ctx` is what this prompt needs, never above
    /// what the model reports; a prompt that cannot fit is an error, not a
    /// silent truncation.
    static func ollamaBody(_ choice: AIChoice, prompt: String, contextLength: Int) throws -> [String: Any] {
        guard prompt.count <= ollamaInputLimit(contextLength: contextLength) else {
            throw LLMError.tooLong("ollama", choice.model, contextLength)
        }
        var body: [String: Any] = [
            "model": choice.model,
            "messages": [["role": "user", "content": prompt]],
            "stream": false,
            "options": ["num_ctx": min(contextLength, prompt.count + ollamaReplyTokens)],
        ]
        switch choice.effort {
        case "": break
        case "true": body["think"] = true
        case "false": body["think"] = false
        default: body["think"] = choice.effort
        }
        return body
    }

    private static func ollamaPost(
        _ url: URL, _ payload: [String: Any], timeout: TimeInterval
    ) async throws -> [String: Any] {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = timeout
        request.setValue("application/json", forHTTPHeaderField: "content-type")
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)
        let (data, response) = try await URLSession.shared.data(for: request)
        if let http = response as? HTTPURLResponse, http.statusCode != 200 {
            throw LLMError.http(http.statusCode, text(data))
        }
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw LLMError.malformedResponse("ollama")
        }
        return json
    }

    private static func ollama(choice: AIChoice, url: URL) -> LLMBackend {
        let showURL = url.deletingLastPathComponent().appendingPathComponent("show")
        let contextLength: @Sendable () async throws -> Int = {
            let show = try await ollamaPost(showURL, ["model": choice.model], timeout: 30)
            guard let length = ollamaContextLength(show) else {
                throw LLMError.unknownContext("ollama", choice.model)
            }
            return length
        }
        var backend = LLMBackend(name: "ollama", model: choice.model) { system, prompt in
            let body = try ollamaBody(
                choice, prompt: "\(system)\n\n\(prompt)", contextLength: try await contextLength())
            let json = try await ollamaPost(url, body, timeout: 1800)
            guard var content = (json["message"] as? [String: Any])?["content"] as? String
            else { throw LLMError.malformedResponse("ollama") }
            // A reasoning model asked without `think` writes its thinking inline.
            if let end = content.range(of: "</think>") {
                content = String(content[end.upperBound...])
            }
            guard !content.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                throw LLMError.emptyResponse("ollama")
            }
            return LLMReply(text: content, model: json["model"] as? String ?? choice.model)
        }
        backend.inputLimit = { ollamaInputLimit(contextLength: try await contextLength()) }
        return backend
    }

    // MARK: -

    /// Where a borrowed CLI lives. The looking is `Tooling`'s job — it knows
    /// about the desktop apps that carry a binary inside them, and about the
    /// version managers that keep one somewhere only the login shell can find.
    static func cliPath(_ name: String) -> String? {
        Tooling.path(for: name)
    }

    private static func text(_ data: Data) -> String {
        String(decoding: data.prefix(400), as: UTF8.self)
    }

    private static func jsonLines(_ data: Data) -> [[String: Any]] {
        String(decoding: data, as: UTF8.self)
            .split(whereSeparator: \.isNewline)
            .compactMap { try? JSONSerialization.jsonObject(with: Data($0.utf8)) as? [String: Any] }
    }

    /// A TOML basic string, for values spliced into `codex -c`.
    private static func toml(_ value: String) -> String {
        "\"" + value.replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"") + "\""
    }

    /// A fresh, empty, owner-only folder for one CLI call, removed afterwards.
    /// Resolved through symlinks, so the path the sandbox is told about is the
    /// one the process actually runs in.
    private static func inEmptyFolder<T>(_ body: (URL) async throws -> T) async throws -> T {
        let made = FileManager.default.temporaryDirectory
            .appendingPathComponent("meetontrack-ai-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(
            at: made, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        let dir = URL(fileURLWithPath: realPath(made.path), isDirectory: true)
        defer { try? FileManager.default.removeItem(at: dir) }
        return try await body(dir)
    }

    /// Run a command with stdin, a deadline, and no shell in between.
    static func run(
        executable: String,
        arguments: [String],
        input: String,
        timeout: TimeInterval,
        currentDirectory: URL? = nil
    ) async throws -> String {
        let result = try await Subprocess.run(
            executable: executable, arguments: arguments,
            input: Data(input.utf8), timeout: timeout, currentDirectory: currentDirectory)
        guard result.status == 0 else {
            throw LLMError.exit(
                Int(result.status),
                String(decoding: result.stderr.prefix(600), as: UTF8.self)
                    + String(decoding: result.stdout.suffix(600), as: UTF8.self))
        }
        return String(decoding: result.stdout, as: UTF8.self)
    }
}

struct LLMReply: Equatable {
    let text: String
    /// The model that answered, as the provider reported it — or the one
    /// asked for, when the provider reports nothing.
    let model: String
}

enum LLMBackendResolution {
    case ready(LLMBackend)
    /// No complete choice for this purpose: ask the person, run nothing.
    case needsChoice
    /// A choice exists and cannot run; the reason is for the person.
    case unavailable(String)

    /// What to tell the person when nothing will run.
    var problem: String? {
        switch self {
        case .ready: return nil
        case .needsChoice: return AIChoice.needsChoiceMessage
        case .unavailable(let reason): return reason
        }
    }
}

enum LLMError: Error, CustomStringConvertible {
    case emptyResponse(String)
    case malformedResponse(String)
    case http(Int, String)
    case exit(Int, String)
    /// The prompt does not fit the model's reported context (tokens).
    case tooLong(String, String, Int)
    /// The provider does not report the model's context length.
    case unknownContext(String, String)

    var description: String {
        switch self {
        case .tooLong(let backend, let model, let length):
            return "\(backend): the text is longer than \(model)'s context of \(length) tokens; choose a model with a longer context"
        case .unknownContext(let backend, let model):
            return "\(backend) does not report the context length of \(model); choose another model in Getting started"
        case .emptyResponse(let backend): return "\(backend) returned nothing"
        case .malformedResponse(let backend): return "\(backend) returned an unexpected shape"
        case .http(let code, let body): return "HTTP \(code): \(body)"
        case .exit(let code, let output): return "exited \(code): \(output)"
        }
    }

    /// Whether this failure is "the subscription or quota is spent" rather
    /// than something broken. Worth saying in the log: it comes back.
    var isUsageLimit: Bool {
        let haystack: String
        switch self {
        case .http(let code, let body):
            if code == 429 { return true }
            haystack = body.lowercased()
        case .exit(_, let output):
            haystack = output.lowercased()
        default:
            return false
        }
        return Self.usageLimitMarkers.contains { haystack.contains($0) }
    }

    /// Whether the same request would plausibly succeed later: no network, a
    /// server that fell over, a local model that isn't running yet.
    ///
    /// This is the distinction between "try again this evening" and "this will
    /// never work" — a summary skipped on a plane must not be written off, and
    /// a malformed answer must not be retried for ever. A spent allowance
    /// counts as transient: it comes back.
    var isTransient: Bool {
        switch self {
        case .http(let code, _):
            return code == 429 || code >= 500
        case .exit(_, let output):
            let haystack = output.lowercased()
            return isUsageLimit || Self.transientMarkers.contains { haystack.contains($0) }
        case .tooLong, .unknownContext:
            // Only another model choice fixes these.
            return false
        case .emptyResponse, .malformedResponse:
            // The model answered; it just answered badly. Repeating the same
            // request is unlikely to change that.
            return false
        }
    }

    private static let usageLimitMarkers = [
        "usage limit", "rate limit", "quota", "limit reached", "out of credit",
        "insufficient_quota", "429",
    ]

    private static let transientMarkers = [
        "connection refused", "could not connect", "network is unreachable",
        "no route to host", "temporary failure in name resolution", "dns",
        "timed out", "timeout", "offline", "connection reset", "econnrefused",
        "service unavailable", "overloaded",
    ]

    /// Classify any error, not just this type — the backends throw URLSession
    /// errors too, and the caller shouldn't have to know which is which.
    static func isTransient(_ error: Error) -> Bool {
        if let llm = error as? LLMError { return llm.isTransient }
        if let url = error as? URLError {
            return [
                URLError.notConnectedToInternet, .networkConnectionLost, .timedOut,
                .cannotFindHost, .cannotConnectToHost, .dnsLookupFailed,
                .internationalRoamingOff, .dataNotAllowed, .resourceUnavailable,
                .secureConnectionFailed,
            ].contains(url.code)
        }
        let posix = (error as NSError)
        if posix.domain == NSPOSIXErrorDomain {
            // ECONNREFUSED (61) is ollama not running; EHOSTUNREACH (65),
            // ENETDOWN (50), ETIMEDOUT (60) are the machine being off-network.
            return [50, 60, 61, 65].contains(posix.code)
        }
        return false
    }

    static func isUsageLimit(_ error: Error) -> Bool {
        (error as? LLMError)?.isUsageLimit ?? false
    }
}
