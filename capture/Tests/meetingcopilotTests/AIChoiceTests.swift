import Foundation
import Testing

@testable import meetingcopilot

/// Deep equality of JSON-shaped values, for expectations.
func sameJSON(_ value: Any?, _ expected: [String: Any]) -> Bool {
    NSDictionary(dictionary: value as? [String: Any] ?? [:]).isEqual(to: expected)
}

/// Summary and speaker naming run on the AI the person chose for them in the
/// shared config (`ai.purposes.summary`, `ai.purposes.speaker_names`) and on
/// nothing else: no default model, no fallback order, no `auto`.
///
/// The fake CLIs here are shell scripts in a temporary folder. Each records
/// its argv one argument per line, its stdin, and the folder it ran in, and
/// prints a canned reply in the provider's own stream format.
struct AIChoiceTests {
    private static let choice = AIChoice(
        provider: "codex", model: "test-model", effort: "high", speed: "priority")

    private func scratch() throws -> URL {
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("meetingcopilot-ai-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return URL(fileURLWithPath: LLMBackend.realPath(dir.path), isDirectory: true)
    }

    private func config(_ purposes: [String: Any]) -> [String: Any] {
        ["ai": ["purposes": purposes]]
    }

    // MARK: - resolving a choice

    @Test("A complete choice is runnable; anything less needs a choice")
    func runnableOnlyWhenComplete() {
        let full: [String: Any] = [
            "provider": "claude", "model": "m", "effort": "", "speed": "",
        ]
        #expect(AIChoice.resolve(.summary, in: config(["summary": full]))
            == .ready(AIChoice(provider: "claude", model: "m", effort: "", speed: "")))

        for key in ["provider", "model", "effort", "speed"] {
            var partial = full
            partial.removeValue(forKey: key)
            #expect(AIChoice.resolve(.summary, in: config(["summary": partial])) == .needsChoice,
                    "missing \(key) must not run")
        }
        var empty = full
        empty["model"] = ""
        #expect(AIChoice.resolve(.summary, in: config(["summary": empty])) == .needsChoice)
        var wrongType = full
        wrongType["effort"] = 3
        #expect(AIChoice.resolve(.summary, in: config(["summary": wrongType])) == .needsChoice)

        #expect(AIChoice.resolve(.summary, in: nil) == .needsChoice)
        #expect(AIChoice.resolve(.speakerNames, in: config(["summary": full])) == .needsChoice,
                "naming has its own choice and does not borrow the summary's")
    }

    @Test("Antigravity is refused for every purpose")
    func antigravityRefused() {
        let agy: [String: Any] = ["provider": "antigravity", "model": "m", "effort": "", "speed": ""]
        for purpose in AIPurpose.allCases {
            let resolved = AIChoice.resolve(purpose, in: config([purpose.rawValue: agy]))
            #expect(resolved == .unavailable(
                "cannot enforce read-only/no-tools: permission_mode always-proceed"))
        }
        // And it never reaches a process.
        if case .ready = LLMBackend.resolve(
            .summary, config: config(["summary": agy]), tool: { _ in "/bin/echo" }) {
            Issue.record("antigravity must not run")
        }
    }

    @Test("A needs-choice purpose says where to choose")
    func needsChoiceSaysWhere() {
        guard case .needsChoice = LLMBackend.resolve(.summary, config: [:], tool: { _ in nil })
        else { Issue.record("an unset purpose must need a choice"); return }
        #expect(AIChoice.needsChoiceMessage.contains("Getting started"))
    }

    // MARK: - exact command lines

    @Test("Codex runs with exactly the isolated argv, the prompt on stdin")
    func codexArgv() async throws {
        let dir = try scratch()
        defer { try? FileManager.default.removeItem(at: dir) }
        let bin = dir.appendingPathComponent("pkg/bin", isDirectory: true)
        try FileManager.default.createDirectory(at: bin, withIntermediateDirectories: true)
        let log = dir.appendingPathComponent("log")
        let codex = try fakeCLI(at: bin.appendingPathComponent("codex"), log: log, reply: """
            {"type":"thread.started"}
            {"type":"item.completed","item":{"type":"agent_message","text":"first"}}
            {"type":"item.completed","item":{"type":"reasoning","text":"thinking"}}
            {"type":"item.completed","item":{"type":"agent_message","text":"the answer"}}
            """)

        let backend = try ready(LLMBackend.resolve(
            .summary, config: config(["summary": [
                "provider": "codex", "model": "test-model", "effort": "high", "speed": "priority",
            ]]), tool: { $0 == "codex" ? codex.path : nil }))
        let reply = try await backend.call("SYSTEM", "PROMPT")
        #expect(reply == LLMReply(text: "the answer", model: "test-model"))

        let ran = try recorded(log)
        let root = dir.appendingPathComponent("pkg").path
        let workdir = ran.cwd
        #expect(ran.args == [
            "--ask-for-approval", "never", "-m", "test-model",
            "-c", #"model_reasoning_effort="high""#,
            "-c", #"service_tier="priority""#,
            "-c", #"default_permissions="meetontrack""#,
            "-c", #"permissions.meetontrack.filesystem={":minimal"="read",""#
                + workdir + #""="read",""# + root + #""="read"}"#,
            "exec", "--ignore-user-config", "--skip-git-repo-check", "--ephemeral",
            "--disable", "shell_tool", "--disable", "unified_exec", "--disable", "multi_agent",
            "--disable", "enable_mcp_apps", "--disable", "skill_search",
            "--disable", "skill_mcp_dependency_install", "--disable", "tool_suggest",
            "-c", #"web_search="disabled""#, "-c", "project_doc_max_bytes=0",
            "-c", "skills.include_instructions=false",
            "-C", workdir, "--json", "-",
        ])
        #expect(ran.stdin == "SYSTEM\n\nPROMPT")
        #expect(ran.emptyCwd, "the work folder must be fresh and empty")
        #expect(!FileManager.default.fileExists(atPath: workdir), "the work folder is removed after")
    }

    @Test("Codex leaves effort and speed out when there are none, and standard means default")
    func codexOptionalFlags() {
        let none = LLMBackend.codexArguments(
            AIChoice(provider: "codex", model: "m", effort: "", speed: ""),
            workdir: "/w", packageRoot: "/p")
        let standard = LLMBackend.codexArguments(
            AIChoice(provider: "codex", model: "m", effort: "", speed: "standard"),
            workdir: "/w", packageRoot: "/p")
        #expect(none == standard)
        #expect(!none.contains { $0.hasPrefix("model_reasoning_effort") || $0.hasPrefix("service_tier") })
    }

    @Test("Codex with no agent message, or a non-zero exit, is a failure")
    func codexFailures() async throws {
        let dir = try scratch()
        defer { try? FileManager.default.removeItem(at: dir) }
        let log = dir.appendingPathComponent("log")
        let silent = try fakeCLI(at: dir.appendingPathComponent("codex"), log: log,
                                 reply: #"{"type":"turn.completed"}"#)
        let choice: [String: Any] = ["provider": "codex", "model": "m", "effort": "", "speed": ""]
        let backend = try ready(LLMBackend.resolve(
            .summary, config: config(["summary": choice]), tool: { _ in silent.path }))
        await #expect(throws: LLMError.self) { try await backend.call("s", "p") }

        let failing = try fakeCLI(at: dir.appendingPathComponent("codex2"), log: log,
                                  reply: #"{"type":"item.completed","item":{"type":"agent_message","text":"x"}}"#,
                                  status: 1)
        let broken = try ready(LLMBackend.resolve(
            .summary, config: config(["summary": choice]), tool: { _ in failing.path }))
        await #expect(throws: LLMError.self) { try await broken.call("s", "p") }
    }

    @Test("Claude runs with exactly the isolated argv and reports the model it used")
    func claudeArgv() async throws {
        let dir = try scratch()
        defer { try? FileManager.default.removeItem(at: dir) }
        let log = dir.appendingPathComponent("log")
        let claude = try fakeCLI(at: dir.appendingPathComponent("claude"), log: log, reply: """
            {"type":"system","subtype":"init","model":"actual-model-id"}
            {"type":"assistant","message":{}}
            {"type":"result","subtype":"success","is_error":false,"result":"the answer"}
            """)

        let backend = try ready(LLMBackend.resolve(
            .speakerNames, config: config(["speaker_names": [
                "provider": "claude", "model": "alias", "effort": "max", "speed": "fastMode",
            ]]), tool: { $0 == "claude" ? claude.path : nil }))
        let reply = try await backend.call("SYSTEM", "PROMPT")
        #expect(reply == LLMReply(text: "the answer", model: "actual-model-id"))

        let ran = try recorded(log)
        #expect(ran.args == [
            "-p", "--output-format", "stream-json", "--verbose",
            "--setting-sources", "", "--strict-mcp-config",
            "--model", "alias", "--effort", "max",
            "--settings", #"{"fastMode":true}"#,
            "--tools", "", "--no-session-persistence",
        ])
        #expect(ran.stdin == "SYSTEM\n\nPROMPT")
        #expect(ran.emptyCwd)
    }

    @Test("Claude without effort or fast mode passes neither")
    func claudeOptionalFlags() {
        let args = LLMBackend.claudeArguments(
            AIChoice(provider: "claude", model: "m", effort: "", speed: "standard"))
        #expect(args == [
            "-p", "--output-format", "stream-json", "--verbose",
            "--setting-sources", "", "--strict-mcp-config", "--model", "m",
            "--tools", "", "--no-session-persistence",
        ])
    }

    @Test("A Claude result flagged as an error is a failure")
    func claudeErrorResult() throws {
        let stdout = Data("""
            {"type":"system","subtype":"init","model":"x"}
            {"type":"result","is_error":true,"result":"Claude usage limit reached"}
            """.utf8)
        #expect(throws: LLMError.self) { try LLMBackend.claudeReply(stdout, requested: "m") }
    }

    @Test("Ollama is asked over /api/chat, with think only when an effort was chosen")
    func ollamaRequest() throws {
        func body(_ effort: String) -> [String: Any] {
            LLMBackend.ollamaBody(
                AIChoice(provider: "ollama", model: "local", effort: effort, speed: ""),
                prompt: "PROMPT")
        }
        let plain = body("")
        #expect(plain["model"] as? String == "local")
        #expect(plain["stream"] as? Bool == false)
        #expect(plain["think"] == nil)
        let messages = try #require(plain["messages"] as? [[String: String]])
        #expect(messages == [["role": "user", "content": "PROMPT"]])
        #expect(body("true")["think"] as? Bool == true)
        #expect(body("false")["think"] as? Bool == false)
        #expect(body("high")["think"] as? String == "high")

        #expect(LLMBackend.ollamaChatURL(environment: [:]).absoluteString
            == "http://127.0.0.1:11434/api/chat")
        #expect(LLMBackend.ollamaChatURL(environment: ["OLLAMA_HOST": "box:1234/"]).absoluteString
            == "http://box:1234/api/chat")
    }

    // MARK: - migrating the old settings once

    @Test("Only explicit legacy keys are migrated, and only to codex, claude or ollama")
    func migrationUsesOnlyExplicitKeys() {
        var codex: [String: Any] = ["summary": ["backend": "codex-cli", "openai_model": "picked"]]
        AIChoice.migrateLegacy(&codex)
        #expect(sameJSON(codex["ai"], [
            "purposes": ["summary": ["provider": "codex", "model": "picked"]],
        ]))

        // A backend with no model written: the provider is kept, nothing is
        // invented for the model, and effort and speed are left for the person.
        var bare: [String: Any] = ["summary": ["backend": "ollama"]]
        AIChoice.migrateLegacy(&bare)
        let migrated = ((bare["ai"] as? [String: Any])?["purposes"] as? [String: Any])?["summary"]
        #expect(sameJSON(migrated, ["provider": "ollama"]))
        #expect(AIChoice.resolve(.summary, in: bare) == .needsChoice)

        for backend in ["auto", "anthropic-api", "openai-api", "none"] {
            var json: [String: Any] = ["summary": ["backend": backend, "model": "m"]]
            AIChoice.migrateLegacy(&json)
            #expect(json["ai"] == nil, "\(backend) must not be migrated")
        }

        var nothing: [String: Any] = ["summary": ["model": "m", "openai_model": "o"]]
        AIChoice.migrateLegacy(&nothing)
        #expect(nothing["ai"] == nil, "a model without a backend is not a choice")

        // An existing choice is never overwritten.
        var chosen: [String: Any] = [
            "summary": ["backend": "codex-cli"],
            "ai": ["purposes": ["summary": ["provider": "claude"]], "other": 1],
        ]
        AIChoice.migrateLegacy(&chosen)
        #expect(sameJSON(chosen["ai"], [
            "purposes": ["summary": ["provider": "claude"]], "other": 1,
        ]))
    }

    @Test("Speaker naming migrates from its own backend")
    func namingMigration() {
        var json: [String: Any] = [
            "speaker_names": ["backend": "claude-cli", "model": "namer"],
            "summary": ["model": "summarizer"],
        ]
        AIChoice.migrateLegacy(&json)
        let purposes = (json["ai"] as? [String: Any])?["purposes"] as? [String: Any]
        #expect(sameJSON(purposes?["speaker_names"], ["provider": "claude", "model": "namer"]))
        #expect(purposes?["summary"] == nil, "the summary had no backend of its own")
    }

    @Test("Migration goes through the locked writer and keeps everything else")
    func migrationWritesTheFile() throws {
        let dir = try scratch()
        defer { try? FileManager.default.removeItem(at: dir) }
        let url = dir.appendingPathComponent("config.json")
        try JSONSerialization.data(withJSONObject: [
            "summary": ["backend": "claude-cli", "model": "picked", "language": "ru"],
            "ai": ["purposes": ["live_analysis": ["provider": "codex"]]],
        ]).write(to: url)

        Config.migrateLegacyAIChoices(file: url)

        let json = try #require(
            JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any])
        let purposes = try #require((json["ai"] as? [String: Any])?["purposes"] as? [String: Any])
        #expect(sameJSON(purposes, [
            "live_analysis": ["provider": "codex"],
            "summary": ["provider": "claude", "model": "picked"],
        ]))
        #expect((json["summary"] as? [String: Any])?["language"] as? String == "ru")
        let mode = try FileManager.default.attributesOfItem(atPath: url.path)[.posixPermissions]
        #expect(mode as? Int == 0o600)
    }

    // MARK: - no model in the source

    @Test("No AI model id is written into the app's source")
    func noModelLiterals() throws {
        let sources = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("Sources")
        let pattern = try NSRegularExpression(
            pattern: #"gpt-[0-9]|claude-(opus|sonnet|haiku)|gemini-[0-9]|qwen[0-9]"#)
        let files = FileManager.default.enumerator(at: sources, includingPropertiesForKeys: nil)?
            .compactMap { $0 as? URL }.filter { $0.pathExtension == "swift" } ?? []
        #expect(!files.isEmpty)
        for file in files {
            let text = try String(contentsOf: file, encoding: .utf8)
            let hits = pattern.matches(in: text, range: NSRange(text.startIndex..., in: text))
            #expect(hits.isEmpty, "a model id in \(file.lastPathComponent)")
        }
    }

    // MARK: - helpers

    private func ready(_ resolution: LLMBackendResolution) throws -> LLMBackend {
        guard case .ready(let backend) = resolution else {
            throw LLMError.malformedResponse("expected a runnable backend, got \(resolution)")
        }
        return backend
    }

    private func fakeCLI(at url: URL, log: URL, reply: String, status: Int = 0) throws -> URL {
        let script = """
            #!/bin/sh
            : > "\(log.path).args"
            for arg in "$@"; do printf '%s\\n' "$arg" >> "\(log.path).args"; done
            cat > "\(log.path).stdin"
            pwd -P > "\(log.path).cwd"
            ls -A | wc -l | tr -d ' ' > "\(log.path).count"
            cat <<'REPLY'
            \(reply)
            REPLY
            exit \(status)
            """
        try Data(script.utf8).write(to: url)
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: url.path)
        return url
    }

    private func recorded(_ log: URL) throws -> (args: [String], stdin: String, cwd: String, emptyCwd: Bool) {
        func read(_ suffix: String) throws -> String {
            try String(contentsOf: URL(fileURLWithPath: log.path + suffix), encoding: .utf8)
        }
        var args = try read(".args").components(separatedBy: "\n")
        if args.last == "" { args.removeLast() }
        let cwd = try read(".cwd").trimmingCharacters(in: .whitespacesAndNewlines)
        let count = try read(".count").trimmingCharacters(in: .whitespacesAndNewlines)
        return (args, try read(".stdin"), cwd, count == "0")
    }
}
