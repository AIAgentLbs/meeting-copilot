import Darwin
import Foundation

/// Finding the command-line tools meetingcopilot borrows — `claude`, `codex`, `ollama`
/// — on a machine where they may not be where a list of three paths expects.
///
/// Three things make this harder than `which`, and each of them produces the
/// same wrong answer ("not installed") about a tool that is sitting right
/// there:
///
/// 1. **The app's PATH is not yours.** macOS hands a launched app a minimal
///    environment, so anything installed through homebrew's node, mise, volta,
///    fnm or bun is invisible to us and visible to you. Asking the login shell
///    is the only way to see what you see.
/// 2. **A desktop app can be the install.** ChatGPT.app carries a working
///    `codex` binary inside its bundle, and someone who has never opened a
///    terminal has it and nothing else.
/// 3. **A file is not a working tool.** A path that exists proves nothing;
///    running it and getting a version back proves everything worth proving,
///    and it is the check that catches the case above where the binary is
///    found but cannot run from where we are.
///
/// Answers are cached for the life of the process: the login shell costs a few
/// hundred milliseconds, `--version` costs a spawn, and neither answer changes
/// often enough to pay that per summary.
enum Tooling {
    /// A tool as far as we can tell — where it is, and what it said when run.
    struct Found: Equatable {
        let name: String
        let path: String
        /// The first line of `--version`. nil means the file is there and did
        /// not answer, which for our purposes is the same as absent — but is
        /// worth saying differently, because the fix is different.
        let version: String?

        var runs: Bool { version != nil }
    }

    /// Well-known install locations, in the order they're tried, `~` for the
    /// home folder. The same list as `copilot/web/tool_locations.json`, which
    /// the web server reads (ToolingLocationsTests keeps the two equal).
    /// `~/.local/bin` is where both official installers put their entry point;
    /// ChatGPT.app carries a working `codex` inside its bundle.
    static let listedLocations: [String: [String]] = [
        "codex": [
            "~/.codex/packages/standalone/current/bin/codex",
            "~/.local/bin/codex",
            "/opt/homebrew/bin/codex",
            "/usr/local/bin/codex",
            "/Applications/ChatGPT.app/Contents/Resources/codex",
        ],
        "claude": ["~/.local/bin/claude", "/opt/homebrew/bin/claude", "/usr/local/bin/claude"],
        "agy": ["~/.local/bin/agy", "/opt/homebrew/bin/agy", "/usr/local/bin/agy"],
        "ollama": ["~/.local/bin/ollama", "/opt/homebrew/bin/ollama", "/usr/local/bin/ollama"],
    ]

    fileprivate static func locations(for name: String) -> [String] {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        return (listedLocations[name] ?? []).map {
            $0.hasPrefix("~/") ? home + $0.dropFirst() : $0
        }
    }

    // MARK: - looking

    /// The path to a tool, or nil. Cheap after the first call.
    static func path(for name: String) -> String? {
        cache.path(for: name)
    }

    /// The tool, run once to see whether it answers. Cheap after the first call.
    static func probe(_ name: String) -> Found? {
        guard let path = path(for: name) else { return nil }
        return Found(name: name, path: path, version: cache.version(of: name, at: path))
    }

    /// Forget what we found, so the next look goes out to the disk and the
    /// shell again — for after someone has installed something and come back.
    static func forget() { cache.clear() }

    /// Whether ollama is answering on its usual port, and with which models.
    /// nil means nothing is listening: not an error, just the common case.
    static func ollamaModels() async -> [String]? {
        var request = URLRequest(url: URL(string: "http://127.0.0.1:11434/api/tags")!)
        request.timeoutInterval = 2
        guard
            let (data, response) = try? await URLSession.shared.data(for: request),
            (response as? HTTPURLResponse)?.statusCode == 200,
            let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let models = json["models"] as? [[String: Any]]
        else { return nil }
        return models.compactMap { $0["name"] as? String }
    }

    // MARK: - the cache

    private static let cache = Cache()

    /// Shared mutable state behind a lock rather than an actor: every caller
    /// here is synchronous, and making them all async to protect two
    /// dictionaries would spread through the summarizer for nothing.
    private final class Cache: @unchecked Sendable {
        private let lock = NSLock()
        /// The pick, with the state of every candidate file it was made from:
        /// an update, reinstall or removal makes it pick again (as the web
        /// server's `_Binary` does).
        private var paths: [String: (signature: String, path: String?)] = [:]
        private var shellPaths: [String: String?] = [:]
        private var versions: [String: String?] = [:]

        func clear() {
            lock.lock()
            defer { lock.unlock() }
            paths = [:]
            shellPaths = [:]
            versions = [:]
        }

        func path(for name: String) -> String? {
            let environment = ProcessInfo.processInfo.environment
            if let override = environment[Tooling.overrideVariable(name)], !override.isEmpty {
                return override
            }
            lock.lock()
            let fromShell: String?
            if let known = shellPaths[name] {
                fromShell = known
                lock.unlock()
            } else {
                lock.unlock()
                fromShell = Tooling.fromLoginShell(name)
                lock.lock()
                shellPaths[name] = fromShell
                lock.unlock()
            }
            let candidates = Tooling.locations(for: name) + [fromShell].compactMap { $0 }
            let signature = candidates.map(Tooling.stamp).joined(separator: "|")
            lock.lock()
            if let known = paths[name], known.signature == signature {
                lock.unlock()
                return known.path
            }
            lock.unlock()

            let found = Tooling.newest(candidates) { Tooling.askVersion(of: $0) }

            lock.lock()
            paths[name] = (signature, found)
            versions[name] = nil
            lock.unlock()
            return found
        }

        func version(of name: String, at path: String) -> String? {
            lock.lock()
            if let known = versions[name] {
                lock.unlock()
                return known
            }
            lock.unlock()

            let answer = Tooling.askVersion(of: path)

            lock.lock()
            versions[name] = answer
            lock.unlock()
            return answer
        }
    }

    // MARK: - the search itself

    /// `MEETING_COPILOT_CODEX` and friends: the same override the web server
    /// honours, checked before any search.
    static func overrideVariable(_ name: String) -> String {
        "MEETING_COPILOT_" + name.uppercased()
    }

    /// One rule for the app and the web server (`first_run.pick_codex`): of the
    /// executable candidates, the one whose `--version` is highest; the first
    /// one when none answers with a version.
    static func newest(_ candidates: [String], version: (String) -> String?) -> String? {
        var seen = Set<String>()
        let existing = candidates.filter {
            FileManager.default.isExecutableFile(atPath: $0) && seen.insert(realPath($0)).inserted
        }
        var best = existing.first
        var bestVersion: [Int] = []
        for candidate in existing {
            let parsed = versionNumbers(version(candidate))
            if parsed.lexicographicallyPrecedes(bestVersion) || parsed == bestVersion { continue }
            best = candidate
            bestVersion = parsed
        }
        return best
    }

    /// The first dotted number in a `--version` line, e.g. "codex-cli 0.159.2" → [0, 159, 2].
    static func versionNumbers(_ line: String?) -> [Int] {
        guard let line, let range = line.range(of: #"\d+(\.\d+)+"#, options: .regularExpression)
        else { return [] }
        return line[range].split(separator: ".").compactMap { Int($0) }
    }

    private static func realPath(_ path: String) -> String {
        guard let pointer = realpath(path, nil) else { return path }
        defer { free(pointer) }
        return String(cString: pointer)
    }

    /// Resolved path, modification time and size: what changes on an update.
    fileprivate static func stamp(_ path: String) -> String {
        let real = realPath(path)
        guard let info = try? FileManager.default.attributesOfItem(atPath: real) else { return "" }
        let modified = (info[.modificationDate] as? Date)?.timeIntervalSince1970 ?? 0
        return "\(real):\(modified):\(info[.size] as? Int ?? 0)"
    }

    /// Ask the user's login shell where the tool is, because that shell is the
    /// only thing that knows about their version manager. Interactive (`-i`)
    /// as well as login (`-l`): on macOS zsh, homebrew's shellenv usually
    /// lives in `.zprofile` but mise, asdf and nvm nearly always live in
    /// `.zshrc`, which only an interactive shell reads.
    ///
    /// Failures here are silent and expected: a shell with a prompt that waits
    /// for something, a shell that isn't zsh or bash, no shell at all.
    fileprivate static func fromLoginShell(_ name: String) -> String? {
        let shell: String = {
            if let fromEnvironment = ProcessInfo.processInfo.environment["SHELL"],
               !fromEnvironment.isEmpty {
                return fromEnvironment
            }
            // A launched app has no SHELL; the account record always has one.
            if let record = getpwuid(getuid()), let shell = record.pointee.pw_shell {
                return String(cString: shell)
            }
            return "/bin/zsh"
        }()
        guard FileManager.default.isExecutableFile(atPath: shell) else { return nil }

        guard let output = run(
            shell, ["-lic", "command -v \(name)"], timeout: 8
        ) else { return nil }

        // `command -v` prints a path, but a login shell prints whatever else
        // the dotfiles feel like printing, so take the last line that looks
        // like an executable rather than trusting the first.
        let path = output
            .split(separator: "\n")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .last { $0.hasPrefix("/") && FileManager.default.isExecutableFile(atPath: $0) }
        return path
    }

    /// Run it. Not "does the file exist" — the whole point of this pass is the
    /// machine where the file exists and running it from here doesn't work.
    fileprivate static func askVersion(of path: String) -> String? {
        guard let output = run(path, ["--version"], timeout: 20) else { return nil }
        let line = output
            .split(separator: "\n")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .first { !$0.isEmpty }
        guard let line, !line.isEmpty else { return nil }
        return String(line.prefix(60))
    }

    /// A subprocess with a deadline and no shell in between, returning stdout
    /// on a clean exit and nil on anything else. Deliberately quiet: every
    /// caller here is asking a question that is allowed to be answered "no".
    private static func run(_ executable: String, _ arguments: [String],
                            timeout: TimeInterval) -> String? {
        guard let result = try? Subprocess.runSync(
            executable: executable, arguments: arguments, timeout: timeout),
              result.status == 0 else { return nil }
        return String(decoding: result.stdout, as: UTF8.self)
    }
}
