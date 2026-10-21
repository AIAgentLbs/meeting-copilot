import FluidAudio
import Foundation

/// The speech models the FluidAudio adapter can run, named the way FluidAudio
/// names them. This file holds adapters, not choices: the families are the
/// FluidAudio enum cases our engines know how to drive, every id is FluidAudio's
/// own repository name (or a ship path from the repository's manifest), and
/// which one runs is the person's `stt.choice`.
enum LocalSTTModel: Equatable, Sendable {
    /// A Parakeet TDT batch model: final transcripts directly, live through
    /// FluidAudio's sliding window.
    case parakeet(AsrModelVersion)
    /// One ship of the multilingual Nemotron streaming repository, by its path
    /// in that repository's `manifest.json` (`<vocabulary>/<chunk>ms`).
    case nemotron(ship: String)

    /// The Parakeet versions this adapter can load (`AsrModelVersion` is not
    /// CaseIterable and keeps its repository internal, hence the mapping).
    static let parakeetVersions: [AsrModelVersion] = [.v3, .v2, .tdtCtc110m, .tdtJa]

    static func repo(for version: AsrModelVersion) -> Repo {
        switch version {
        case .v3: return .parakeetV3
        case .v2: return .parakeetV2
        case .tdtCtc110m: return .parakeetTdtCtc110m
        case .tdtJa: return .parakeetJa
        }
    }

    static let nemotronRepo = Repo.nemotronMultilingual

    var id: String {
        switch self {
        case .parakeet(let version): return Self.repo(for: version).name
        case .nemotron(let ship): return "\(Self.nemotronRepo.name)/\(ship)"
        }
    }

    var family: String {
        switch self {
        case .parakeet: return "parakeet-tdt"
        case .nemotron: return "nemotron-streaming"
        }
    }

    var repo: Repo {
        switch self {
        case .parakeet(let version): return Self.repo(for: version)
        case .nemotron: return Self.nemotronRepo
        }
    }

    var sourceURL: String {
        "\(ModelRegistry.baseURL)/\(repo.remotePath)"
    }

    /// Chunk length of a Nemotron ship, read from its path (`…/1120ms`).
    var chunkMilliseconds: Int? {
        guard case .nemotron(let ship) = self,
              let last = ship.split(separator: "/").last, last.hasSuffix("ms")
        else { return nil }
        return Int(last.dropLast(2))
    }

    static func parse(_ id: String) -> LocalSTTModel? {
        if let version = parakeetVersions.first(where: { repo(for: $0).name == id }) {
            return .parakeet(version)
        }
        let prefix = "\(nemotronRepo.name)/"
        guard id.hasPrefix(prefix) else { return nil }
        let ship = String(id.dropFirst(prefix.count))
        guard !ship.isEmpty, !ship.split(separator: "/").contains(where: { $0 == ".." || $0 == "." }),
              !ship.hasPrefix("/")
        else { return nil }
        return .nemotron(ship: ship)
    }

    /// The model an old `transcription.model` value named, for the one-time
    /// migration only: `v3` and `v2` were the two values the old setting took.
    static func legacyParakeet(_ value: String) -> LocalSTTModel? {
        switch value {
        case "v3": return .parakeet(.v3)
        case "v2": return .parakeet(.v2)
        default: return nil
        }
    }

    // MARK: - files

    static var modelsRoot: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("FluidAudio", isDirectory: true)
            .appendingPathComponent("Models", isDirectory: true)
    }

    var directory: URL {
        switch self {
        case .parakeet(let version):
            return AsrModels.defaultCacheDirectory(for: version)
        case .nemotron(let ship):
            return Self.modelsRoot
                .appendingPathComponent(Self.nemotronRepo.folderName, isDirectory: true)
                .appendingPathComponent(ship, isDirectory: true)
        }
    }

    /// The file names FluidAudio downloads for a Parakeet version, for sizing
    /// a model before it is downloaded. The encoder precision is FluidAudio's
    /// own default (ponytail: int4 is not offered as a choice).
    var requiredParakeetFiles: Set<String> {
        guard case .parakeet(let version) = self else { return [] }
        let names: Set<String>
        switch version {
        case .tdtJa: names = ModelNames.TDTJa.requiredModels
        case .v3: names = ModelNames.ASR.requiredModelsV3()
        default:
            names = version.hasFusedEncoder
                ? ModelNames.ASR.requiredModelsFused : ModelNames.ASR.requiredModels
        }
        return names.union([ModelNames.ASR.vocabulary(for: Self.repo(for: version))])
    }

    /// Our folder for this model's repository: where FluidAudio loads from.
    var repoFolder: URL {
        switch self {
        case .parakeet: return directory
        case .nemotron: return Self.modelsRoot.appendingPathComponent(Self.nemotronRepo.folderName, isDirectory: true)
        }
    }

    /// Whether a path in the repository's tree is a file this model needs.
    func includes(_ path: String) -> Bool {
        switch self {
        case .parakeet:
            let top = path.split(separator: "/").first.map(String.init) ?? path
            return requiredParakeetFiles.contains(top)
        case .nemotron(let ship):
            return path.hasPrefix(ship + "/") && !path.contains(".mlpackage")
        }
    }

    /// The Hugging Face listing of this model's files.
    var treeURL: URL? {
        switch self {
        case .parakeet: return try? ModelRegistry.apiModels(repo.remotePath, "tree/main?recursive=true")
        case .nemotron(let ship):
            return try? ModelRegistry.apiModels(repo.remotePath, "tree/main/\(ship)?recursive=true")
        }
    }

    var isDownloaded: Bool {
        switch self {
        case .parakeet(let version):
            return AsrModels.modelsExist(at: directory, version: version)
        case .nemotron:
            return Self.nemotronVariantReady(at: directory)
        }
    }

    /// A complete Nemotron ship needs its metadata and tokenizer, the encoder
    /// and one decode path. Checking more than FluidAudio's metadata marker
    /// tells an interrupted download from a model that can load.
    static func nemotronVariantReady(at dir: URL) -> Bool {
        let exists: (String) -> Bool = { name in
            FileManager.default.fileExists(atPath: dir.appendingPathComponent(name).path)
        }
        guard exists("metadata.json"), exists("tokenizer.json"),
              exists("encoder.mlmodelc") || exists("encoder.mlpackage")
        else { return false }
        let fused = ["decoder_joint_argmax", "decoder_joint_noencproj", "decoder_joint"]
            .contains { exists("\($0).mlmodelc") || exists("\($0).mlpackage") }
        let split = (exists("decoder.mlmodelc") || exists("decoder.mlpackage"))
            && (exists("joint.mlmodelc") || exists("joint.mlpackage"))
        return fused || split
    }

    /// The prompt languages a downloaded Nemotron ship accepts, from its own
    /// metadata. nil when the ship is not on disk.
    var localNemotronPrompts: [String]? {
        guard case .nemotron = self else { return nil }
        return Self.nemotronPrompts(metadata: try? Data(
            contentsOf: directory.appendingPathComponent("metadata.json")))
    }

    static func nemotronPrompts(metadata: Data?) -> [String]? {
        guard let metadata,
              let json = try? JSONSerialization.jsonObject(with: metadata) as? [String: Any],
              let prompts = json["prompt_dictionary"] as? [String: Any]
        else { return nil }
        return prompts.keys.sorted()
    }

    /// The languages this Mac knows the model takes without the network: a
    /// ship's own prompt list on disk, or the cached model card. nil when
    /// neither is here.
    var offlineLanguages: [String]? {
        switch self {
        case .nemotron: return localNemotronPrompts?.filter { $0 != STTChoice.autoLanguage }
        case .parakeet: return STTCatalog.cachedCardLanguages(self)
        }
    }

    /// When this model's folder last changed: its download or update, the
    /// person's own last action with it.
    var modified: Date? {
        (try? directory.resourceValues(forKeys: [.contentModificationDateKey]))?.contentModificationDate
    }

    /// The speech models in our own model folders, complete: what the
    /// installer (or an earlier setup) downloaded. Other apps' folders do not
    /// count; nobody here chose those.
    static var installed: [LocalSTTModel] {
        parakeetVersions.map { .parakeet($0) }.filter(\.isDownloaded)
            + STTCatalog.localNemotronShips().map { .nemotron(ship: $0) }
    }

    /// `STTChoice.impliedLanguage` from what this Mac knows without the
    /// network: a Nemotron ship's own prompt list, or a Parakeet model card
    /// in the discovery cache.
    var offlineImpliedLanguage: String? {
        switch self {
        case .nemotron:
            guard let prompts = localNemotronPrompts else { return nil }
            return STTChoice.impliedLanguage(
                languages: prompts.filter { $0 != STTChoice.autoLanguage },
                autoDetect: prompts.contains(STTChoice.autoLanguage))
        case .parakeet:
            let languages = STTCatalog.cachedCardLanguages(self)
            return STTChoice.impliedLanguage(languages: languages, autoDetect: languages.map { $0.count > 1 })
        }
    }

    /// Download this model into FluidAudio's cache. The only caller is
    /// `stt-download`, which is the only place downloads are switched on.
    func download(progress: ProgressHandler?) async throws {
        await STTReuse.adopt(repo: repo, ours: repoFolder, treeURL: treeURL, include: includes)
        switch self {
        case .parakeet(let version):
            try await AsrModels.download(version: version, progressHandler: progress)
        case .nemotron(let ship):
            if !isDownloaded {
                // metadata.json is FluidAudio's cache-complete marker; after an
                // interrupted download only the marker goes, so the repair pass
                // reuses every intact file.
                try? FileManager.default.removeItem(
                    at: directory.appendingPathComponent("metadata.json"))
            }
            try await ModelHub.download(
                Self.nemotronRepo,
                subdirectory: ship,
                to: Self.modelsRoot.appendingPathComponent(Self.nemotronRepo.folderName),
                progressHandler: progress,
                shouldSkip: { $0.contains(".mlpackage") })
            guard isDownloaded else {
                throw STTRuntime.Failure("the download finished but \(id) is incomplete")
            }
        }
    }
}

/// A speaker separation model for the far-end track: one LS-EEND variant at
/// one step size, named the way FluidAudio names it (`ls_eend_dih3_500ms`).
/// Not a setting (owner decision 2026-10-21: no speaker prompt); the live
/// transcript uses whichever is on this Mac.
struct LocalSpeakerModel: Equatable, Sendable {
    let variant: LSEENDVariant
    let step: LSEENDStepSize

    static var all: [LocalSpeakerModel] {
        LSEENDVariant.allCases.flatMap { variant in
            LSEENDStepSize.allCases.map { LocalSpeakerModel(variant: variant, step: $0) }
        }
    }

    /// The speaker models in our own model folder.
    static var installed: [LocalSpeakerModel] { all.filter(\.isDownloaded) }

    /// Fetched with every local speech model so that voices are told apart
    /// live and after the call without anyone being asked (owner decision
    /// 2026-10-21). It is an internal component of speaker separation, not a
    /// model a person chooses, so it is outside the no-hardcoded-models rule,
    /// which covers user choices. It is the model main fetched on first live
    /// use (LS-EEND DIHARD3, 500 ms step).
    static let companion = LocalSpeakerModel(variant: .dihard3, step: .step500ms)

    /// From the shared FluidAudio folder when it is already there.
    func download() async throws {
        guard !isDownloaded else { return }
        try await ModelHub.download(variant.repo, subdirectory: relativePath, to: repoDirectory)
    }

    var id: String { variant.name(forStep: step) }

    static func parse(_ id: String) -> LocalSpeakerModel? {
        all.first { $0.id == id }
    }

    /// Path inside the repository, which is also the path under the repo's
    /// cache folder: the layout `LSEENDModel.loadFromHuggingFace` uses.
    var relativePath: String {
        let file = variant.fileName(forStep: step)
        return variant.repo.subPath.map { "\($0)/\(file)" } ?? file
    }

    var repoDirectory: URL {
        LocalSTTModel.modelsRoot.appendingPathComponent(variant.repo.folderName, isDirectory: true)
    }

    var url: URL { repoDirectory.appendingPathComponent(relativePath, isDirectory: true) }

    /// The compiled bundle's own files, not just its folder: an interrupted
    /// download leaves the folder behind, and the next download resumes it.
    var isDownloaded: Bool { Self.bundleComplete(at: url) }

    static func bundleComplete(at bundle: URL) -> Bool {
        ["coremldata.bin", "model.mil", "metadata.json", "weights/weight.bin"].allSatisfy {
            FileManager.default.fileExists(atPath: bundle.appendingPathComponent($0).path)
        }
    }
}
