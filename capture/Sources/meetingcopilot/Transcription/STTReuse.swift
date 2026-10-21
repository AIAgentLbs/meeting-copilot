import CryptoKit
import FluidAudio
import Foundation

/// Speech model files that are already on this Mac in another FluidAudio
/// folder: an older FluidAudio release used a different folder name
/// (`parakeet-tdt-0.6b-v3-coreml` instead of `parakeet-tdt-0.6b-v3`), and
/// other FluidAudio-based apps (FluidVoice) share the same cache root or use
/// `~/.cache/fluidaudio/Models`. FluidAudio itself only looks in its current
/// folder, so without this a second copy of the same weights is downloaded.
///
/// Reuse is read-only towards the other folder: a file is copied into our
/// folder (an APFS clone, so no extra disk) only after its content hash
/// matches the one the model host publishes, and nothing in the other folder
/// is ever changed or deleted. Whatever is still missing is then downloaded.
enum STTReuse {
    /// One file of a model as the Hugging Face tree lists it.
    struct RemoteFile: Equatable, Sendable {
        let path: String
        let size: Int
        /// Git blob sha1 of the content (every file).
        let gitOID: String?
        /// sha256 of the content (LFS files).
        let sha256: String?

        init(path: String, size: Int, gitOID: String?, sha256: String?) {
            self.path = path
            self.size = size
            self.gitOID = gitOID
            self.sha256 = sha256
        }

        init?(_ entry: [String: Any]) {
            guard entry["type"] as? String == "file", let path = entry["path"] as? String else { return nil }
            let lfs = entry["lfs"] as? [String: Any]
            self.init(
                path: path,
                size: (lfs?["size"] as? Int) ?? (entry["size"] as? Int) ?? 0,
                gitOID: entry["oid"] as? String,
                sha256: lfs?["oid"] as? String)
        }

        /// Whether the file at `url` is this file: same size, same content hash.
        func matches(_ url: URL) -> Bool {
            guard Self.size(of: url) == size else { return false }
            if let sha256 { return Self.sha256(of: url) == sha256 }
            if let gitOID { return Self.gitBlobSHA1(of: url) == gitOID }
            return false
        }

        static func size(of url: URL) -> Int? {
            let values = try? url.resourceValues(forKeys: [.isRegularFileKey, .fileSizeKey])
            guard values?.isRegularFile == true else { return nil }
            return values?.fileSize
        }

        static func sha256(of url: URL) -> String? {
            guard let handle = try? FileHandle(forReadingFrom: url) else { return nil }
            defer { try? handle.close() }
            var hash = SHA256()
            while let chunk = try? handle.read(upToCount: 1 << 22), !chunk.isEmpty { hash.update(data: chunk) }
            return hash.finalize().map { String(format: "%02x", $0) }.joined()
        }

        static func gitBlobSHA1(of url: URL) -> String? {
            guard let size = size(of: url), let handle = try? FileHandle(forReadingFrom: url) else { return nil }
            defer { try? handle.close() }
            var hash = Insecure.SHA1()
            hash.update(data: Data("blob \(size)\0".utf8))
            while let chunk = try? handle.read(upToCount: 1 << 22), !chunk.isEmpty { hash.update(data: chunk) }
            return hash.finalize().map { String(format: "%02x", $0) }.joined()
        }
    }

    /// Model roots FluidAudio-based apps write to: the current default and
    /// the `~/.cache` location some FluidAudio builds use. Sandboxed apps'
    /// containers are not read (macOS asks the person before an app reads
    /// another app's data).
    static var roots: [URL] {
        [
            LocalSTTModel.modelsRoot,
            FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent(".cache/fluidaudio/Models", isDirectory: true),
        ]
    }

    /// Other folders that may hold this repository's files: every root under
    /// FluidAudio's current folder name and the older one (the repository
    /// name, which older releases used), minus our own folder.
    static func candidates(for repo: Repo, own: URL, roots: [URL] = roots) -> [URL] {
        let names = Array(Set([repo.folderName, repo.name]))
        let ownPath = own.standardizedFileURL.path
        return roots.flatMap { root in names.map { root.appendingPathComponent($0, isDirectory: true) } }
            .filter { $0.standardizedFileURL.path != ownPath }
            .filter { FileManager.default.fileExists(atPath: $0.path) }
            .sorted { $0.path < $1.path }
    }

    struct Plan: Equatable {
        /// Files our folder lacks that another folder has with the same size.
        var reusable: [(file: RemoteFile, source: URL)]
        /// Bytes that still have to be downloaded.
        var downloadBytes: Int
        /// The other folders that contribute, with how much each would save.
        var sources: [(folder: URL, bytes: Int)]

        static func == (lhs: Plan, rhs: Plan) -> Bool {
            lhs.reusable.map(\.file) == rhs.reusable.map(\.file)
                && lhs.reusable.map(\.source) == rhs.reusable.map(\.source)
                && lhs.downloadBytes == rhs.downloadBytes
                && lhs.sources.map(\.folder) == rhs.sources.map(\.folder)
                && lhs.sources.map(\.bytes) == rhs.sources.map(\.bytes)
        }
    }

    /// What can be reused from `candidates` for the files `ours` lacks. Sizes
    /// only, so discovery stays fast; `adopt` checks the hashes before use.
    static func plan(files: [RemoteFile], ours: URL, candidates: [URL]) -> Plan {
        var plan = Plan(reusable: [], downloadBytes: 0, sources: [])
        var saved: [URL: Int] = [:]
        for file in files {
            if FileManager.default.fileExists(atPath: ours.appendingPathComponent(file.path).path) { continue }
            if let source = candidates.first(where: {
                RemoteFile.size(of: $0.appendingPathComponent(file.path)) == file.size
            }) {
                plan.reusable.append((file, source))
                saved[source, default: 0] += file.size
            } else {
                plan.downloadBytes += file.size
            }
        }
        plan.sources = saved.sorted { $0.key.path < $1.key.path }.map { ($0.key, $0.value) }
        return plan
    }

    /// Clone every reusable file whose hash matches into our folder. Returns
    /// the bytes reused. A file that does not match is left to the download.
    @discardableResult
    static func adopt(files: [RemoteFile], ours: URL, candidates: [URL]) -> Int {
        let fm = FileManager.default
        var reused = 0
        for (file, source) in plan(files: files, ours: ours, candidates: candidates).reusable {
            let from = source.appendingPathComponent(file.path)
            let to = ours.appendingPathComponent(file.path)
            guard file.matches(from) else { continue }
            do {
                try fm.createDirectory(at: to.deletingLastPathComponent(), withIntermediateDirectories: true)
                // copyItem clones on APFS: same blocks, no second copy on disk.
                try fm.copyItem(at: from, to: to)
                reused += file.size
            } catch {
                try? fm.removeItem(at: to)
            }
        }
        return reused
    }

    /// Before a download: reuse what another folder already has. Without a
    /// listing (offline, nothing cached) there is nothing to verify against,
    /// so nothing is reused and the download fetches everything.
    @discardableResult
    static func adopt(
        repo: Repo, ours: URL, treeURL: URL?, include: (String) -> Bool
    ) async -> Int {
        let candidates = candidates(for: repo, own: ours)
        guard !candidates.isEmpty,
              let tree = await STTCatalog.Fetcher(cache: STTCatalog.Fetcher.defaultCache, refresh: false)
                .json(treeURL).0 as? [[String: Any]]
        else { return 0 }
        return adopt(files: files(tree: tree, where: include), ours: ours, candidates: candidates)
    }

    /// The reuse facts for a model entry in `stt-options`.
    static func describe(
        tree: [[String: Any]]?, repo: Repo, ours: URL, downloaded: Bool, include: (String) -> Bool
    ) -> [String: Any] {
        guard !downloaded else { return ["download_bytes": 0, "found_elsewhere": [[String: Any]]()] }
        guard let tree else { return ["download_bytes": NSNull(), "found_elsewhere": [[String: Any]]()] }
        let plan = plan(
            files: files(tree: tree, where: include), ours: ours,
            candidates: candidates(for: repo, own: ours))
        return [
            "download_bytes": plan.downloadBytes,
            "found_elsewhere": plan.sources.map { ["path": $0.folder.path, "bytes": $0.bytes] },
        ]
    }

    /// The files a model needs, from its Hugging Face tree.
    static func files(tree: [[String: Any]], where include: (String) -> Bool) -> [RemoteFile] {
        tree.compactMap(RemoteFile.init).filter { include($0.path) }
    }
}
