import CryptoKit
import FluidAudio
import Foundation
import Testing

@testable import meetingcopilot

/// MEETONTRACK-45: a model another FluidAudio folder already holds (the older
/// `-coreml` folder name, FluidVoice's copy) is reused after its hash checks
/// out, and the other folder is never touched.
struct STTReuseTests {
    private let root: URL
    private let ours: URL
    private let old: URL

    init() throws {
        root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meetontrack-reuse-\(UUID().uuidString)", isDirectory: true)
        ours = root.appendingPathComponent(Repo.parakeetV3.folderName, isDirectory: true)
        old = root.appendingPathComponent(Repo.parakeetV3.name, isDirectory: true)
        try FileManager.default.createDirectory(at: old, withIntermediateDirectories: true)
    }

    private func put(_ text: String, _ path: String, in folder: URL) throws -> STTReuse.RemoteFile {
        let url = folder.appendingPathComponent(path)
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        let data = Data(text.utf8)
        try data.write(to: url)
        let sha = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        return STTReuse.RemoteFile(path: path, size: data.count, gitOID: nil, sha256: sha)
    }

    private func snapshot(_ folder: URL) -> [String: Data] {
        let files = FileManager.default.enumerator(at: folder, includingPropertiesForKeys: nil)?
            .compactMap { $0 as? URL }.filter { STTReuse.RemoteFile.size(of: $0) != nil } ?? []
        return Dictionary(uniqueKeysWithValues: files.map {
            ($0.path.replacingOccurrences(of: folder.path, with: ""), (try? Data(contentsOf: $0)) ?? Data())
        })
    }

    @Test("The older folder name is found, our own folder is not")
    func candidatesUseBothNames() throws {
        defer { try? FileManager.default.removeItem(at: root) }
        #expect(Repo.parakeetV3.name != Repo.parakeetV3.folderName)
        try FileManager.default.createDirectory(at: ours, withIntermediateDirectories: true)
        let found = STTReuse.candidates(for: .parakeetV3, own: ours, roots: [root])
        #expect(found.map(\.lastPathComponent) == [Repo.parakeetV3.name])
    }

    @Test("Matching files are cloned in, a changed one is downloaded, the old folder stays as it was")
    func adoptVerifiesAndLeavesTheSourceAlone() throws {
        defer { try? FileManager.default.removeItem(at: root) }
        let encoder = try put("encoder weights", "Encoder.mlmodelc/weights/weight.bin", in: old)
        let decoder = try put("decoder weights", "Decoder.mlmodelc/weights/weight.bin", in: old)
        // Same size as the published file, different content: must not pass.
        var joint = try put("joint-v2", "JointDecisionv3.mlmodelc/weights/weight.bin", in: old)
        joint = STTReuse.RemoteFile(
            path: joint.path, size: joint.size, gitOID: nil,
            sha256: SHA256.hash(data: Data("joint-v3".utf8)).map { String(format: "%02x", $0) }.joined())
        let vocab = STTReuse.RemoteFile(path: "vocab.json", size: 10, gitOID: nil, sha256: "00")
        let files = [encoder, decoder, joint, vocab]
        let before = snapshot(old)

        let plan = STTReuse.plan(files: files, ours: ours, candidates: [old])
        #expect(plan.reusable.map(\.file.path) == [encoder.path, decoder.path, joint.path])
        #expect(plan.downloadBytes == vocab.size)
        #expect(plan.sources.map(\.bytes) == [encoder.size + decoder.size + joint.size])

        let reused = STTReuse.adopt(files: files, ours: ours, candidates: [old])
        #expect(reused == encoder.size + decoder.size)
        #expect(try Data(contentsOf: ours.appendingPathComponent(encoder.path)) == Data("encoder weights".utf8))
        #expect(!FileManager.default.fileExists(atPath: ours.appendingPathComponent(joint.path).path))
        #expect(snapshot(old) == before)

        // Once ours has the files, only the rest is still to download.
        let after = STTReuse.plan(files: files, ours: ours, candidates: [old])
        #expect(after.reusable.map(\.file.path) == [joint.path])
        #expect(after.downloadBytes == vocab.size)
    }

    @Test("A git blob id verifies small files the host lists without sha256")
    func gitBlobHash() throws {
        defer { try? FileManager.default.removeItem(at: root) }
        let url = old.appendingPathComponent("config.json")
        try Data("hello\n".utf8).write(to: url)
        // `git hash-object` of "hello\n".
        let file = STTReuse.RemoteFile(
            path: "config.json", size: 6, gitOID: "ce013625030ba8dba906f756967f9e9ca394464a", sha256: nil)
        #expect(file.matches(url))
        #expect(!STTReuse.RemoteFile(path: "config.json", size: 6, gitOID: "00", sha256: nil).matches(url))
    }

    @Test("A model already present costs no download; without a listing the size is unknown")
    func describe() throws {
        defer { try? FileManager.default.removeItem(at: root) }
        let present = STTReuse.describe(tree: nil, repo: .parakeetV3, ours: ours, downloaded: true) { _ in true }
        #expect(present["download_bytes"] as? Int == 0)
        let unknown = STTReuse.describe(tree: nil, repo: .parakeetV3, ours: ours, downloaded: false) { _ in true }
        #expect(unknown["download_bytes"] is NSNull)
    }
}

/// Live speaker separation is unchanged from main when a speaker model is
/// on this Mac; without one it is never downloaded and the channels label
/// the speakers.
struct LiveDiarizerChoiceTests {
    @Test("No speaker model on this Mac means channel labels, not a download")
    func noSpeakerModelNoDiarizer() async {
        #expect(await LiveTranscriptionCoordinator.remoteDiarizer(installed: []) == nil)
    }

    @Test("A local model download brings the speaker model, and its failure fails nothing")
    func speakerModelRidesAlong() async throws {
        #expect(LocalSpeakerModel.companion.id == "ls_eend_dih3_500ms")
        let missing = try #require(LocalSpeakerModel.all.first { !$0.isDownloaded })
        let failed = await STTDownload.speakerModel(missing) { _ in throw URLError(.notConnectedToInternet) }
        #expect(failed["event"] as? String == "note")
        #expect(failed["state"] as? String == "failed")
        let fetched = await STTDownload.speakerModel(missing) { _ in }
        #expect(fetched["state"] as? String == "downloaded")
        if let present = LocalSpeakerModel.installed.first {
            let reused = await STTDownload.speakerModel(present) { _ in Issue.record("fetched a model already here") }
            #expect(reused["state"] as? String == "present")
        }
    }
}
