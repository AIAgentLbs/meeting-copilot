import FluidAudio
import Foundation
import Testing

@testable import meetingcopilot

/// What the models on the disk weigh and which of them are listed.
///
/// Every one of these can be answered without a model: the sizes are read off
/// directories this suite builds under a temporary root.
struct ModelStorageTests {
    /// A directory with `count` files of a kilobyte each, and nothing else.
    @discardableResult
    private static func directory(_ root: URL, _ name: String, files: Int) throws -> URL {
        let dir = root.appendingPathComponent(name, isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        for index in 0..<files {
            try Data(repeating: 0, count: 1024)
                .write(to: dir.appendingPathComponent("part-\(index).bin"))
        }
        return dir
    }

    private static func temporary() throws -> URL {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("model-storage-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        return root
    }

    @Test("A directory's size is what its files add up to, and an absent one is zero")
    func measuring() throws {
        let root = try Self.temporary()
        defer { try? FileManager.default.removeItem(at: root) }

        let dir = try Self.directory(root, "cache", files: 3)
        #expect(ModelStorage.bytes(of: dir) == 3 * 1024)
        #expect(ModelStorage.bytes(of: root.appendingPathComponent("nothing here")) == 0)
    }

    @Test("Only models whose files are on disk are listed, each under its own id")
    func listing() throws {
        let root = try Self.temporary()
        defer { try? FileManager.default.removeItem(at: root) }
        let storage = ModelStorage(root: root)
        #expect(storage.all().isEmpty)

        let parakeet = LocalSTTModel.parakeet(.v2)
        try Self.directory(root, LocalSTTModel.repo(for: .v2).folderName, files: 2)

        // A Nemotron ship is the folder holding metadata.json; a Core ML
        // bundle inside it carries a file of the same name and is not a ship.
        let ship = try Self.directory(
            root, "\(LocalSTTModel.nemotronRepo.folderName)/en/160ms", files: 1)
        try Data("{}".utf8).write(to: ship.appendingPathComponent("metadata.json"))
        let bundle = try Self.directory(ship, "encoder.mlmodelc", files: 1)
        try Data("{}".utf8).write(to: bundle.appendingPathComponent("metadata.json"))

        let speaker = try #require(LocalSpeakerModel.all.first)
        try Self.directory(
            root, "\(speaker.variant.repo.folderName)/\(speaker.relativePath)", files: 1)

        let models = storage.all()
        #expect(models.map(\.name) == [
            parakeet.id, "\(LocalSTTModel.nemotronRepo.name)/en/160ms", speaker.id,
        ])
        #expect(models.map(\.kind) == [.speech, .speech, .speaker])
        #expect(models.allSatisfy { $0.isDownloaded })
        #expect(storage.total(models) == 2 * 1024 + (2 * 1024 + 4) + 1024)

        try storage.delete(models[1])
        #expect(storage.all().map(\.name) == [parakeet.id, speaker.id])
        // Deleting what is already gone is what a second click on a stale
        // window is, and it is not an error.
        try storage.delete(models[1])
    }

    /// A test process is in English and nothing here changes that: the
    /// language a size is written in is `InterfaceLanguageTests`' question,
    /// and the suite that flips the language for the whole program is the
    /// only one that should.
    @Test("A size is rounded to something a person reads")
    func describing() {
        #expect(ModelStorage.describe(bytes: 461 * 1_048_576) == "461 MB")
        #expect(ModelStorage.describe(bytes: 0) == "0 MB")
        // Past a thousand megabytes the number stops being one anybody reads.
        #expect(ModelStorage.describe(bytes: 1_147_483_648) == "1.1 GB")
    }
}
