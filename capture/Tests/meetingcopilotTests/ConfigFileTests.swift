import Darwin
import Foundation
import Testing

@testable import meetingcopilot

/// The write protocol every component of the shared config.json agrees on
/// (docs/config.schema.json): one advisory lock, a whole-file
/// read-modify-replace, mode 0600, and a file that cannot be parsed is never
/// mistaken for an empty one.
///
/// Every test works on a config in its own temporary folder; none of them may
/// touch the person's real ~/.config/meeting-copilot/config.json.
struct ConfigFileTests {
    private func scratchConfig() throws -> URL {
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("meetingcopilot-config-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("config.json")
    }

    private func object(at url: URL) throws -> [String: Any] {
        try #require(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any])
    }

    private func mode(of url: URL) throws -> Int {
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        return try #require(attributes[.posixPermissions] as? Int)
    }

    @Test("A missing config reads as missing and the first save creates it with mode 0600")
    func missingFileIsEmptyAndSavable() throws {
        let url = try scratchConfig()
        defer { try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }

        guard case .missing = ConfigFile.read(url) else {
            Issue.record("a file that isn't there must read as missing")
            return
        }
        #expect(try ConfigFile.update(url) { $0["keep_audio"] = true })
        #expect(try object(at: url)["keep_audio"] as? Bool == true)
        #expect(try mode(of: url) == 0o600)
    }

    @Test("A malformed or non-object config blocks the save and stays byte-identical")
    func malformedBlocksUpdate() throws {
        let url = try scratchConfig()
        defer { try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }

        for bytes in ["{\"summary\": {\"enabled\": tru", "[1, 2, 3]", ""] {
            let before = Data(bytes.utf8)
            try before.write(to: url)
            guard case .unreadable = ConfigFile.read(url) else {
                Issue.record("\(bytes.debugDescription) must read as unreadable, not as a config")
                continue
            }
            #expect(throws: ConfigFile.Unreadable.self) {
                try ConfigFile.update(url) { $0["keep_audio"] = true }
            }
            #expect(try Data(contentsOf: url) == before)
            // The error names the file, so whoever reads it knows what to fix.
            do {
                try ConfigFile.update(url) { $0["keep_audio"] = true }
            } catch {
                #expect("\(error)".contains(url.path))
            }
        }
    }

    @Test("Config.update refuses to save over a malformed file and reports it")
    func configUpdateRefusesMalformed() throws {
        let url = try scratchConfig()
        defer { try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }
        let before = Data("{ not json".utf8)
        try before.write(to: url)

        #expect(!Config.update(file: url, path: ["keep_audio"], value: true))
        #expect(try Data(contentsOf: url) == before)
        #expect(Config.loadProblem(at: url)?.contains(url.path) == true)
    }

    @Test("The saved file is 0600 even when the old one was readable by others")
    func resultIsOwnerOnly() throws {
        let url = try scratchConfig()
        defer { try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }
        try Data("{}".utf8).write(to: url)
        chmod(url.path, 0o644)

        #expect(try ConfigFile.update(url) { $0["window"] = false })
        #expect(try mode(of: url) == 0o600)
        // No temporary file is left beside it.
        let names = try FileManager.default.contentsOfDirectory(
            atPath: url.deletingLastPathComponent().path)
        #expect(Set(names) == ["config.json", "config.json.lock"])
    }

    @Test("Keys this component does not own survive a save, the ai section included")
    func unknownKeysPreserved() throws {
        let url = try scratchConfig()
        defer { try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }
        let ai: [String: Any] = ["choice": [
            "provider": "codex", "model": "some-model", "effort": "high", "speed": "",
        ], "purposes": ["live_analysis": ["provider": "codex"]]]
        try JSONSerialization.data(withJSONObject: [
            "ai": ai,
            "web": ["port": 8765, "nested": ["a": [1, 2]]],
            "summary": ["language": "ru"],
        ]).write(to: url)

        #expect(Config.update(file: url, path: ["summary", "enabled"], value: false))

        let after = try object(at: url)
        #expect(sameJSON(after["ai"], ai))
        #expect(sameJSON(after["web"], ["port": 8765, "nested": ["a": [1, 2]]]))
        #expect((after["summary"] as? [String: Any])?["language"] as? String == "ru")
        #expect((after["summary"] as? [String: Any])?["enabled"] as? Bool == false)
    }

    @Test("Concurrent updates from many threads lose none of them")
    func concurrentUpdatesLoseNothing() throws {
        let url = try scratchConfig()
        defer { try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }
        let count = 48

        DispatchQueue.concurrentPerform(iterations: count) { index in
            _ = Config.update(file: url, path: ["stress", "key\(index)"], value: index)
        }

        let stress = try #require(try object(at: url)["stress"] as? [String: Any])
        #expect(stress.count == count)
        for index in 0..<count { #expect(stress["key\(index)"] as? Int == index) }
    }

    @Test("A save waits while another holder has the lock, then happens")
    func updateWaitsForTheLock() throws {
        let url = try scratchConfig()
        defer { try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }

        // Another holder, exactly as the Python side takes it.
        let holder = open(url.path + ".lock", O_RDWR | O_CREAT, 0o600)
        try #require(holder >= 0)
        #expect(flock(holder, LOCK_EX) == 0)

        let done = DispatchSemaphore(value: 0)
        // Its own thread: under a busy full suite a global-queue block can
        // start after the timeout below and read as a lost save.
        Thread {
            _ = Config.update(file: url, path: ["keep_audio"], value: true)
            done.signal()
        }.start()
        #expect(done.wait(timeout: .now() + 0.5) == .timedOut, "the save did not wait for the lock")
        #expect(!FileManager.default.fileExists(atPath: url.path))

        close(holder)  // closing releases the lock
        #expect(done.wait(timeout: .now() + 5) == .success)
        #expect(try object(at: url)["keep_audio"] as? Bool == true)
    }
}
