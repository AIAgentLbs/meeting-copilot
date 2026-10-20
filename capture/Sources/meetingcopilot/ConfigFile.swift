import Darwin
import Foundation

/// The shared config.json as a file, read and replaced the way every component
/// that writes it has agreed to (docs/config.schema.json): the Python web app
/// owns the `ai` section, this app owns its own, and each keeps what it does
/// not own.
///
/// - Writers serialize on the advisory lock `config.json.lock` beside the
///   file, held with `flock(LOCK_EX)` across the whole read-modify-replace.
///   The Python side takes the same lock with `fcntl.flock`.
/// - A file that cannot be parsed is never treated as an empty one: saving
///   over it would delete every other component's settings.
/// - The new contents go to a temporary file in the same folder, created
///   0600 before a byte is written, fsynced, then renamed over the old one.
enum ConfigFile {
    enum Contents {
        case missing
        case object([String: Any])
        /// Unreadable, not JSON, or JSON that is not an object.
        case unreadable(String)
    }

    struct Unreadable: Error, CustomStringConvertible {
        let path: URL
        let reason: String
        var description: String {
            "\(path.path) \(reason) — fix or remove it; settings are not saved until then"
        }
    }

    static func read(_ url: URL) -> Contents { load(url).contents }

    /// Change the file under the lock. Returns whether it was written: a
    /// change that leaves the bytes as they are writes nothing.
    @discardableResult
    static func update(_ url: URL, _ change: (inout [String: Any]) throws -> Void) throws -> Bool {
        let dir = url.deletingLastPathComponent()
        try FileManager.default.createDirectory(
            at: dir, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])

        let lock = open(url.path + ".lock", O_RDWR | O_CREAT | O_CLOEXEC, 0o600)
        guard lock >= 0 else { throw posixError() }
        defer { close(lock) }  // closing releases the lock
        while flock(lock, LOCK_EX) != 0 {
            guard errno == EINTR else { throw posixError() }
        }

        var json: [String: Any]
        let (contents, current) = load(url)
        switch contents {
        case .missing: json = [:]
        case .object(let object): json = object
        case .unreadable(let reason): throw Unreadable(path: url, reason: reason)
        }
        try change(&json)
        // Sorted keys and a stable formatter, so identical settings really do
        // produce identical bytes rather than a diff in key order.
        let data = try JSONSerialization.data(
            withJSONObject: json, options: [.prettyPrinted, .sortedKeys])
        if data == current { return false }
        try replace(url, with: data)
        return true
    }

    private static func load(_ url: URL) -> (contents: Contents, data: Data?) {
        let data: Data
        do {
            data = try Data(contentsOf: url)
        } catch {
            let ns = error as NSError
            if ns.domain == NSCocoaErrorDomain, ns.code == NSFileReadNoSuchFileError {
                return (.missing, nil)
            }
            return (.unreadable("can't be read (\(ns.localizedDescription))"), nil)
        }
        guard let parsed = try? JSONSerialization.jsonObject(with: data) else {
            return (.unreadable("is not valid JSON"), data)
        }
        guard let object = parsed as? [String: Any] else {
            return (.unreadable("does not hold a JSON object"), data)
        }
        return (.object(object), data)
    }

    private static func replace(_ url: URL, with data: Data) throws {
        let temp = url.deletingLastPathComponent()
            .appendingPathComponent(".\(url.lastPathComponent).\(UUID().uuidString).tmp")
        let fd = open(temp.path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0o600)
        guard fd >= 0 else { throw posixError() }
        var renamed = false
        defer { if !renamed { unlink(temp.path) } }

        do {
            defer { close(fd) }
            // The open mode is filtered by umask; say 0600 outright, before
            // anything is in the file.
            guard fchmod(fd, 0o600) == 0 else { throw posixError() }
            try data.withUnsafeBytes { (raw: UnsafeRawBufferPointer) in
                guard let base = raw.baseAddress else { return }
                var offset = 0
                while offset < raw.count {
                    let written = Darwin.write(fd, base + offset, raw.count - offset)
                    if written < 0 {
                        if errno == EINTR { continue }
                        throw posixError()
                    }
                    offset += written
                }
            }
            guard fsync(fd) == 0 else { throw posixError() }
        }
        guard rename(temp.path, url.path) == 0 else { throw posixError() }
        renamed = true
    }

    private static func posixError() -> POSIXError {
        POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO)
    }
}
