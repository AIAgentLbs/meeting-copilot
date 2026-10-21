import Foundation

/// The local speech models as files on a disk: which of them are on this Mac,
/// what they weigh, and how to get the space back.
///
/// Only what is actually there is listed. Which model to use is chosen in
/// Getting started (`stt.choice`), so there is no configured model to show
/// as missing here; a model is listed because its files exist, and its size
/// is measured off the disk rather than quoted.
///
/// Deleting changes no setting. A deleted model that is still the chosen one
/// makes speech recognition report it as not downloaded, and Getting started
/// is where it comes back.
struct ModelStorage {
    /// One model, as a person is shown it.
    struct Model: Equatable {
        enum Kind: Equatable {
            /// Speech recognition: a Parakeet version or a Nemotron ship.
            case speech
            /// Speaker separation for the far-end track.
            case speaker
        }

        let kind: Kind
        /// The model id, as `stt.choice` names it.
        let name: String
        let directory: URL
        /// What the directory holds, in bytes.
        let bytes: Int

        var isDownloaded: Bool { bytes > 0 }
    }

    /// FluidAudio's model cache. A seam so tests never see the real one.
    let root: URL

    init(root: URL = LocalSTTModel.modelsRoot) {
        self.root = root
    }

    /// Every model this app can run whose files are on this Mac: Parakeet
    /// versions, then Nemotron ships, then speaker models.
    func all() -> [Model] {
        let parakeet = LocalSTTModel.parakeetVersions.map { version in
            model(.speech, LocalSTTModel.parakeet(version).id,
                  root.appendingPathComponent(LocalSTTModel.repo(for: version).folderName))
        }
        let speakers = LocalSpeakerModel.all.map { speaker in
            model(.speaker, speaker.id,
                  root.appendingPathComponent(speaker.variant.repo.folderName)
                      .appendingPathComponent(speaker.relativePath))
        }
        return (parakeet + nemotronShips() + speakers).filter(\.isDownloaded)
    }

    /// A ship is any folder under the Nemotron repository that holds the
    /// `metadata.json` FluidAudio writes. Core ML bundles carry a file of the
    /// same name, so they are not looked inside.
    private func nemotronShips() -> [Model] {
        let repo = root.appendingPathComponent(LocalSTTModel.nemotronRepo.folderName)
            .resolvingSymlinksInPath()
        guard let walker = FileManager.default.enumerator(at: repo, includingPropertiesForKeys: nil)
        else { return [] }
        var ships: [Model] = []
        for case let url as URL in walker {
            if ["mlmodelc", "mlpackage"].contains(url.pathExtension) {
                walker.skipDescendants()
            } else if url.lastPathComponent == "metadata.json" {
                let dir = url.deletingLastPathComponent().resolvingSymlinksInPath()
                let ship = dir.path.dropFirst(repo.path.count + 1)
                ships.append(model(.speech, "\(LocalSTTModel.nemotronRepo.name)/\(ship)", dir))
            }
        }
        return ships.sorted { $0.name < $1.name }
    }

    private func model(_ kind: Model.Kind, _ name: String, _ directory: URL) -> Model {
        Model(kind: kind, name: name, directory: directory, bytes: Self.bytes(of: directory))
    }

    /// What everything listed comes to.
    func total(_ models: [Model]) -> Int {
        models.reduce(0) { $0 + $1.bytes }
    }

    /// Remove the model's whole directory: FluidAudio writes more into it
    /// than it reads back, and a half-emptied cache is the state its
    /// downloader is worst at recovering from.
    func delete(_ model: Model) throws {
        guard FileManager.default.fileExists(atPath: model.directory.path) else { return }
        try FileManager.default.removeItem(at: model.directory)
    }

    /// A size as a person reads it: megabytes until they stop being readable,
    /// and the decimal separator the window's language uses rather than the
    /// one `String(format:)` picks.
    static func describe(bytes: Int) -> String {
        let megabytes = Double(bytes) / 1_048_576
        guard megabytes >= 1024 else {
            return localised("\(Int(megabytes.rounded())) MB", "\(Int(megabytes.rounded())) МБ")
        }
        let gigabytes = String(format: "%.1f", megabytes / 1024)
        return localised(
            "\(gigabytes) GB",
            gigabytes.replacingOccurrences(of: ".", with: ",") + " ГБ")
    }

    /// What a directory holds, in bytes.
    static func bytes(of directory: URL) -> Int {
        guard let walker = FileManager.default.enumerator(
            at: directory, includingPropertiesForKeys: [.fileSizeKey]
        ) else { return 0 }
        var total = 0
        for case let url as URL in walker {
            total += (try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0
        }
        return total
    }
}
