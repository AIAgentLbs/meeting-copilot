import FluidAudio
import Foundation

/// Discovery for the speech recognition choice: contract
/// `meetontrack.stt-options/1` (docs/specs/2026-10-20-no-hardcoded-models.md,
/// Phase 3). Every list comes from the engine or its model host: FluidAudio's
/// own enumerations and cache layout, the Hugging Face model card, tree and
/// manifest, OpenAI's model list, never from a list written here.
///
/// Built as plain JSON objects so unknown facts stay `null` in the output
/// rather than disappearing.
enum STTCatalog {
    static let contract = "meetontrack.stt-options/1"
    static let liveUnavailable = "no live transcript for this engine yet"

    /// An engine's own name, for every place a person reads the choice:
    /// Getting started gets it in `label`, the setup form beside the model.
    /// The stored id (`fluidaudio`) is a key, never shown.
    static func engineName(_ id: String) -> String {
        switch id {
        case STTChoice.localEngine: return "FluidAudio"
        case "assemblyai": return "AssemblyAI"
        case "openai": return "OpenAI"
        default: return id
        }
    }

    /// The name a person reads for a model, in parts, so each window composes
    /// it in its own language: the base ("Parakeet v3"), a variant (a ship's
    /// path, "latin, 1120 ms") and the languages the model lists (their count,
    /// and the code when there is only one). Derived from the model's own
    /// metadata, never from a table of names.
    struct NameParts: Equatable {
        let base: String
        let variant: String
        let languageCount: Int?
        let language: String?

        var json: [String: Any] {
            ["base": base, "variant": variant,
             "language_count": languageCount ?? NSNull(), "language": language ?? NSNull()]
        }

        /// The same composition speech.js makes for the web page.
        func composed(in interface: InterfaceLanguage) -> String {
            let name = variant.isEmpty ? base : "\(base), \(variant)"
            if let language {
                let spoken = Locale(identifier: interface.rawValue).localizedString(forLanguageCode: language)
                return "\(name) (\(spoken ?? language))"
            }
            guard let count = languageCount, count > 1 else { return name }
            return name + " (\(Self.languages(count, in: interface)))"
        }

        /// "5 languages"; "21 язык", "2 языка", "5 языков": the CLDR plural
        /// forms speech.js gets from Intl.PluralRules.
        static func languages(_ count: Int, in interface: InterfaceLanguage) -> String {
            guard interface == .russian else { return "\(count) " + (count == 1 ? "language" : "languages") }
            let (ones, tens) = (count % 10, count % 100)
            let form = ones == 1 && tens != 11 ? "язык"
                : (2...4).contains(ones) && !(12...14).contains(tens) ? "языка" : "языков"
            return "\(count) \(form)"
        }
    }

    /// A FluidAudio repository name gives its family and version (or size,
    /// when it has no version) and a ship its path. A name the provider's own
    /// API returns (`provided`) is used as it is. Any other id (a cloud model,
    /// a speaker model) keeps its own casing with separators as spaces:
    /// `some-Model_v2` reads "some Model v2".
    static func nameParts(_ id: String, languages: [String]?, provided: String? = nil) -> NameParts {
        func matches(_ word: String, _ pattern: String) -> Bool {
            word.range(of: pattern, options: [.regularExpression, .caseInsensitive]) != nil
        }
        var base: String, variant: [String] = []
        let path = id.split(separator: "/").map(String.init)
        if let provided, !provided.isEmpty {
            base = provided
        } else if LocalSTTModel.parse(id) != nil, let repo = path.first {
            let words = repo.split(separator: "-").map(String.init).filter { $0.lowercased() != "coreml" }
            let version = words.dropFirst().first { matches($0, #"^(v\d+(\.\d+)*|\d+(\.\d+)+)$"#) }
            let size = words.first { matches($0, #"^\d+(\.\d+)?[mb]$"#) }?.uppercased()
            let family = words.first ?? repo
            base = ([family.prefix(1).uppercased() + family.dropFirst()] + [version ?? size].compactMap { $0 })
                .joined(separator: " ")
            // A ship's own path: `latin/1120ms` reads "latin, 1120 ms".
            variant = path.dropFirst().map {
                $0.replacingOccurrences(of: #"^(\d+)ms$"#, with: "$1 ms", options: .regularExpression)
            }
        } else {
            base = id.replacingOccurrences(of: "[-_/]+", with: " ", options: .regularExpression)
        }
        let known = languages.flatMap { $0.isEmpty ? nil : $0 }
        let one = known?.count == 1 ? known?[0].split(separator: "-").first.map(String.init) : nil
        return NameParts(base: base, variant: variant.joined(separator: ", "), languageCount: known?.count, language: one)
    }

    /// The composed name; stt-options carries the English one as `display_name`.
    /// `parakeet-tdt-0.6b-v3-coreml` with 25 languages: "Parakeet v3 (25 languages)".
    static func displayName(_ id: String, languages: [String]?, in language: InterfaceLanguage = .english) -> String {
        nameParts(id, languages: languages).composed(in: language)
    }

    /// `display_name` and `name_parts` for a model entry.
    static func named(_ parts: NameParts) -> [String: Any] {
        ["display_name": parts.composed(in: .english), "name_parts": parts.json]
    }

    /// The same name for a stored model id, with the languages this Mac knows
    /// without the network (a ship on disk, a cached model card).
    static func displayName(_ id: String, in language: InterfaceLanguage = InterfaceLanguage.current) -> String {
        displayName(id, languages: LocalSTTModel.parse(id)?.offlineLanguages, in: language)
    }

    struct Inputs {
        var stored: [String: Any]?
        var resolution: STTResolution
        var localModels: Bool
        var fetch: Fetcher
        var openAIKey: String?
        var assemblyAIKey: String?
    }

    static func options(refresh: Bool) async -> [String: Any] {
        Config.migrateLegacySpeechChoice()
        let stored = STTChoice.stored(in: Config.current())
        var result = await options(Inputs(
            stored: stored,
            resolution: STTRuntime.resolve(stored: stored),
            localModels: Platform.supportsLocalModels,
            fetch: Fetcher(cache: Fetcher.defaultCache, refresh: refresh),
            openAIKey: Config.openAIKey(),
            assemblyAIKey: Config.assemblyAIKey()))
        guard stored == nil else { return result }
        // The one installed model's language may only now be known (its
        // model card was just read), which completes the carried-over choice.
        let implied = impliedLanguages(result)
        Config.migrateLegacySpeechChoice(language: { implied[$0.id] ?? nil })
        if let adopted = STTChoice.stored(in: Config.current()) {
            let resolution = STTRuntime.resolve(stored: adopted)
            result["choice"] = ["stored": adopted, "state": resolution.state, "reason": resolution.reason,
                                "name_parts": choiceName(adopted, engines: result["engines"] as? [[String: Any]] ?? [])]
        }
        return result
    }

    /// `STTChoice.impliedLanguage` for every local model in an options result.
    static func impliedLanguages(_ options: [String: Any]) -> [String: String?] {
        let engines = options["engines"] as? [[String: Any]] ?? []
        let local = engines.first { $0["id"] as? String == STTChoice.localEngine }
        var out: [String: String?] = [:]
        for model in local?["models"] as? [[String: Any]] ?? [] {
            guard let id = model["id"] as? String else { continue }
            out[id] = STTChoice.impliedLanguage(
                languages: model["languages"] as? [String], autoDetect: model["auto_detect"] as? Bool)
        }
        return out
    }

    static func options(_ inputs: Inputs) async -> [String: Any] {
        let local = await fluidAudio(inputs)
        let openAI = await openAI(inputs)
        return [
            "contract": contract,
            "generated_at": ISO8601DateFormatter().string(from: Date()),
            "platform": [
                "os": "macos",
                "arch": Platform.architecture,
                "local_models": inputs.localModels,
            ],
            "choice": [
                "stored": inputs.stored.map { $0 as Any } ?? NSNull(),
                "state": inputs.resolution.state,
                "reason": inputs.resolution.reason,
                "name_parts": choiceName(inputs.stored, engines: [local, openAI]),
            ],
            "engines": [local, assemblyAI(inputs), openAI],
        ]
    }

    /// The stored choice's model by the name parts its engine entry lists, or
    /// by the generic rule for a model no listing has (a typed cloud model id).
    static func choiceName(_ stored: [String: Any]?, engines: [[String: Any]]) -> Any {
        guard let model = stored?["model"] as? String, !model.isEmpty else { return NSNull() }
        let listed = engines.filter { $0["id"] as? String == stored?["engine"] as? String }
            .flatMap { $0["models"] as? [[String: Any]] ?? [] }
            .first { $0["id"] as? String == model }
        return listed?["name_parts"] as? [String: Any] ?? nameParts(model, languages: nil).json
    }

    // MARK: - FluidAudio

    static func fluidAudio(_ inputs: Inputs) async -> [String: Any] {
        var engine = engineBase(
            id: STTChoice.localEngine, label: "\(engineName(STTChoice.localEngine)) (on this Mac)", kind: "local",
            available: inputs.localModels,
            reason: inputs.localModels ? "" : "local speech models need a Mac with Apple Silicon",
            needsKey: false, hasKey: nil, modelEntry: "list")
        var errors: [String] = []

        let fetch = inputs.fetch
        let parakeet = await withTaskGroup(of: (Int, SendableJSON).self) { group in
            for (index, version) in LocalSTTModel.parakeetVersions.enumerated() {
                group.addTask { (index, await parakeetEntry(.parakeet(version), fetch).sendable) }
            }
            var out: [(Int, SendableJSON)] = []
            for await entry in group { out.append(entry) }
            return out.sorted { $0.0 < $1.0 }.map(\.1.value)
        }
        let (nemotron, nemotronError) = await nemotronEntries(inputs.fetch)
        if let nemotronError { errors.append(nemotronError) }

        var models = parakeet + nemotron
        if !inputs.localModels {
            models = models.map { var model = $0; model["available"] = false
                model["reason"] = engine["reason"]; return model }
        }
        engine["models"] = models
        engine["listing"] = [
            "source": "FluidAudio adapters (Parakeet TDT, Nemotron streaming) + \(ModelRegistry.baseURL)",
            "error": errors.joined(separator: "; "),
        ]
        return engine
    }

    static func parakeetEntry(_ model: LocalSTTModel, _ fetch: Fetcher) async -> [String: Any] {
        let remote = model.repo.remotePath
        let (cardJSON, cardError) = await fetch.json(cardURL(remote))
        let (treeJSON, _) = await fetch.json(try? ModelRegistry.apiModels(remote, "tree/main?recursive=true"))

        let languages = cardLanguages(cardJSON)
        let size = parakeetSize(tree: treeJSON as? [[String: Any]], files: model.requiredParakeetFiles)
        let config = SlidingWindowAsrConfig.streaming
        var entry = modelBase(model)
        entry["final"] = true
        entry["live"] = "sliding_window"
        entry["live_latency_ms"] = Int((config.chunkSeconds + config.rightContextSeconds) * 1000)
        entry["languages"] = languages ?? []
        entry.merge(named(nameParts(model.id, languages: languages))) { $1 }
        entry["auto_detect"] = languages.map { $0.count > 1 } ?? NSNull()
        entry["size_bytes"] = size.bytes ?? NSNull()
        entry["size_is_estimate"] = size.estimate
        entry.merge(STTReuse.describe(
            tree: treeJSON as? [[String: Any]], repo: model.repo, ours: model.repoFolder,
            downloaded: model.isDownloaded, include: model.includes)) { $1 }
        if languages == nil {
            entry["available"] = false
            entry["reason"] = "could not read the model's languages: \(cardError ?? "no answer")"
        }
        return entry
    }

    /// The model card's language list (a string or a list of strings).
    static func cardLanguages(_ card: Any?) -> [String]? {
        let data = (card as? [String: Any])?["cardData"] as? [String: Any]
        if let list = data?["language"] as? [String], !list.isEmpty { return list }
        if let one = data?["language"] as? String, !one.isEmpty { return [one] }
        return nil
    }

    /// The model's card (`/api/models/<repo>`), which carries `cardData.language`.
    static func cardURL(_ remotePath: String) -> URL? {
        URL(string: "\(ModelRegistry.baseURL)/api/models/\(remotePath)")
    }

    /// The card languages for a Parakeet model from the discovery cache only,
    /// for the offline check in `STTRuntime`.
    static func cachedCardLanguages(_ model: LocalSTTModel) -> [String]? {
        guard let url = cardURL(model.repo.remotePath),
            let data = Fetcher(cache: Fetcher.defaultCache, refresh: false).cached(url),
            let json = try? JSONSerialization.jsonObject(with: data)
        else { return nil }
        return cardLanguages(json)
    }

    /// The languages a downloaded Nemotron ship serves, as discovery lists
    /// them: its prompts narrowed by the cached manifest (a vocabulary-pruned
    /// ship keeps the full prompt dictionary). nil without the manifest.
    static func cachedNemotronLanguages(_ model: LocalSTTModel) -> [String]? {
        guard case .nemotron(let path) = model, let prompts = model.localNemotronPrompts,
            let url = try? ModelRegistry.resolveModel(model.repo.remotePath, "manifest.json"),
            let data = Fetcher(cache: Fetcher.defaultCache, refresh: false).cached(url),
            let ships = (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["ships"] as? [[String: Any]],
            let ship = ships.first(where: { $0["path"] as? String == path })
        else { return nil }
        return nemotronLanguages(prompts: prompts, served: ship["languages_served"] as? [String])
    }

    /// Sum of the tree entries FluidAudio downloads. An estimate when one of
    /// the names it asks for is not in the listing.
    static func parakeetSize(tree: [[String: Any]]?, files: Set<String>) -> (bytes: Int?, estimate: Bool) {
        guard let tree else { return (nil, false) }
        var seen: Set<String> = []
        var total = 0
        for entry in tree where entry["type"] as? String == "file" {
            guard let path = entry["path"] as? String,
                  let top = path.split(separator: "/").first.map(String.init),
                  files.contains(top)
            else { continue }
            seen.insert(top)
            total += size(of: entry)
        }
        guard !seen.isEmpty else { return (nil, false) }
        return (total, seen != files)
    }

    private static func size(of entry: [String: Any]) -> Int {
        ((entry["lfs"] as? [String: Any])?["size"] as? Int) ?? (entry["size"] as? Int) ?? 0
    }

    static func nemotronEntries(_ fetch: Fetcher) async -> ([[String: Any]], String?) {
        let repo = LocalSTTModel.nemotronRepo
        let (manifest, error) = await fetch.json(try? ModelRegistry.resolveModel(repo.remotePath, "manifest.json"))
        guard let ships = (manifest as? [String: Any])?["ships"] as? [[String: Any]] else {
            // Without the manifest only ships already on disk can be listed.
            let local = localNemotronShips().map { path in
                nemotronEntry(ship: ["path": path], metadata: try? Data(contentsOf: LocalSTTModel.nemotron(ship: path)
                    .directory.appendingPathComponent("metadata.json")), tree: nil)
            }
            return (local, "\(repo.name) manifest: \(error ?? "unreadable")")
        }
        let entries = await withTaskGroup(of: (Int, SendableJSON).self) { group in
            for (index, ship) in ships.enumerated() {
                guard let path = ship["path"] as? String else { continue }
                let shipJSON = ship.sendable
                group.addTask {
                    let model = LocalSTTModel.nemotron(ship: path)
                    let metadata: Data? = model.isDownloaded
                        ? (try? Data(contentsOf: model.directory.appendingPathComponent("metadata.json")))
                        : await fetch.data(try? ModelRegistry.resolveModel(repo.remotePath, "\(path)/metadata.json")).0
                    let tree = await fetch.json(try? ModelRegistry.apiModels(
                        repo.remotePath, "tree/main/\(path)?recursive=true")).0
                    return (index, nemotronEntry(
                        ship: shipJSON.value, metadata: metadata, tree: tree as? [[String: Any]]).sendable)
                }
            }
            var out: [(Int, SendableJSON)] = []
            for await entry in group { out.append(entry) }
            return out.sorted { $0.0 < $1.0 }.map(\.1.value)
        }
        return (entries, nil)
    }

    static func localNemotronShips() -> [String] {
        let root = LocalSTTModel.modelsRoot.appendingPathComponent(LocalSTTModel.nemotronRepo.folderName)
        let fm = FileManager.default
        return ((try? fm.contentsOfDirectory(atPath: root.path)) ?? []).sorted().flatMap { vocabulary in
            ((try? fm.contentsOfDirectory(atPath: root.appendingPathComponent(vocabulary).path)) ?? [])
                .sorted().map { "\(vocabulary)/\($0)" }
                .filter { LocalSTTModel.nemotron(ship: $0).isDownloaded }
        }
    }

    static func nemotronEntry(ship: [String: Any], metadata: Data?, tree: [[String: Any]]?) -> [String: Any] {
        let path = ship["path"] as? String ?? ""
        let model = LocalSTTModel.nemotron(ship: path)
        var entry = modelBase(model)
        let prompts = LocalSTTModel.nemotronPrompts(metadata: metadata)
        let languages = prompts.map { nemotronLanguages(prompts: $0, served: ship["languages_served"] as? [String]) }
        entry["final"] = true
        entry["live"] = "streaming"
        entry["live_latency_ms"] = (ship["chunk_ms"] as? Int) ?? model.chunkMilliseconds ?? NSNull()
        entry["languages"] = languages ?? []
        entry.merge(named(nameParts(model.id, languages: languages))) { $1 }
        entry["auto_detect"] = prompts.map { $0.contains(STTChoice.autoLanguage) } ?? NSNull()
        if let tree {
            entry["size_bytes"] = tree.filter { $0["type"] as? String == "file" }
                .filter { !(($0["path"] as? String) ?? "").contains(".mlpackage") }
                .reduce(0) { $0 + size(of: $1) }
        }
        entry["benchmarks"] = ((ship["benchmarks"] as? [[String: Any]]) ?? []).map {
            [
                "language": $0["language_code"] ?? NSNull(),
                "metric": $0["metric"] ?? NSNull(),
                "value": $0["wer_pct"] ?? $0["value"] ?? NSNull(),
                "test_set": $0["test_set"] ?? NSNull(),
            ]
        }
        entry.merge(STTReuse.describe(
            tree: tree, repo: model.repo, ours: model.repoFolder,
            downloaded: model.isDownloaded, include: model.includes)) { $1 }
        if languages == nil {
            entry["available"] = false
            entry["reason"] = "could not read the model's languages (metadata.json)"
        }
        return entry
    }

    /// Prompt keys of a ship, narrowed to the languages the manifest says the
    /// ship serves when that is a list of language codes (a vocabulary-pruned
    /// ship still carries the full prompt dictionary). `auto` is reported as
    /// `auto_detect`, not as a language.
    static func nemotronLanguages(prompts: [String], served: [String]?) -> [String] {
        let codes = served ?? []
        let isCodeList = !codes.isEmpty && codes.allSatisfy {
            $0.range(of: "^[a-z]{2,3}$", options: .regularExpression) != nil
        }
        return prompts.filter { key in
            guard key != STTChoice.autoLanguage else { return false }
            guard isCodeList else { return true }
            let base = key.split(separator: "-").first.map { String($0).lowercased() } ?? key
            return codes.contains(base)
        }
    }

    private static func modelBase(_ model: LocalSTTModel) -> [String: Any] {
        [
            "id": model.id, "label": model.id, "family": model.family,
            "final": NSNull(), "live": "", "live_latency_ms": NSNull(), "live_reason": "",
            "languages": [String](), "language_entry": "list", "auto_detect": NSNull(),
            "speakers": false,
            "size_bytes": NSNull(), "size_is_estimate": false,
            "downloaded": model.isDownloaded,
            "download_bytes": NSNull(), "found_elsewhere": [[String: Any]](),
            "on_disk_bytes": onDisk(model.directory) ?? NSNull(),
            "available": true, "reason": "",
            "source_url": model.sourceURL,
            "benchmarks": [[String: Any]](),
        ].merging(named(nameParts(model.id, languages: nil))) { $1 }
    }

    private static func onDisk(_ url: URL) -> Int? {
        let bytes = ModelStorage.bytes(of: url)
        return bytes > 0 ? bytes : nil
    }

    // MARK: - cloud

    static func cloudModel(id: String, final: Any, speakers: Any, provided: String? = nil) -> [String: Any] {
        [
            "id": id, "label": id, "family": "",
            "final": final, "live": "", "live_latency_ms": NSNull(), "live_reason": liveUnavailable,
            "languages": [String](), "language_entry": "free_text", "auto_detect": true,
            "speakers": speakers,
            "size_bytes": NSNull(), "size_is_estimate": false,
            "downloaded": NSNull(), "download_bytes": NSNull(), "found_elsewhere": [[String: Any]](),
            "on_disk_bytes": NSNull(),
            "available": true, "reason": "", "source_url": "",
            "benchmarks": [[String: Any]](),
        ].merging(named(nameParts(id, languages: nil, provided: provided))) { $1 }
    }

    static func assemblyAI(_ inputs: Inputs) -> [String: Any] {
        let hasKey = inputs.assemblyAIKey != nil
        var engine = engineBase(
            id: "assemblyai", label: engineName("assemblyai"), kind: "cloud",
            available: hasKey, reason: hasKey ? "" : "no AssemblyAI API key",
            needsKey: true, hasKey: hasKey, modelEntry: "free_text")
        engine["listing"] = [
            "source": "none",
            "error": "AssemblyAI publishes no model list endpoint; type the model id and press Check",
        ]
        // Multichannel requests with speaker labels: AssemblyAI separates voices itself.
        engine["model_template"] = cloudModel(id: "", final: true, speakers: true)
        if let stored = storedModel(for: "assemblyai", inputs) {
            engine["models"] = [cloudModel(id: stored, final: true, speakers: true)]
        }
        return engine
    }

    static func openAI(_ inputs: Inputs) async -> [String: Any] {
        guard let key = inputs.openAIKey else {
            var engine = engineBase(
                id: "openai", label: engineName("openai"), kind: "cloud", available: false,
                reason: "no OpenAI API key", needsKey: true, hasKey: false, modelEntry: "list")
            engine["listing"] = ["source": "GET https://api.openai.com/v1/models", "error": "no OpenAI API key"]
            return engine
        }
        var engine = engineBase(
            id: "openai", label: engineName("openai"), kind: "cloud", available: true, reason: "",
            needsKey: true, hasKey: true, modelEntry: "list")
        let (found, error) = await inputs.fetch.openAIModels(key: key)
        var listed = found ?? []
        if let stored = storedModel(for: "openai", inputs), !listed.contains(where: { $0.id == stored }) {
            listed.append((stored, nil))
        }
        // Which of these transcribe, and with speakers, OpenAI does not say
        // until a request is made: unknown (null) until Check runs.
        engine["models"] = listed.map { cloudModel(id: $0.id, final: NSNull(), speakers: NSNull(), provided: $0.name) }
        engine["listing"] = ["source": "GET https://api.openai.com/v1/models", "error": error ?? ""]
        return engine
    }

    private static func storedModel(for engine: String, _ inputs: Inputs) -> String? {
        guard inputs.stored?["engine"] as? String == engine,
              let model = (inputs.stored?["model"] as? String)?.trimmingCharacters(in: .whitespaces),
              !model.isEmpty
        else { return nil }
        return model
    }

    private static func engineBase(
        id: String, label: String, kind: String, available: Bool, reason: String,
        needsKey: Bool, hasKey: Bool?, modelEntry: String
    ) -> [String: Any] {
        [
            "id": id, "label": label, "kind": kind,
            "available": available, "reason": reason,
            "needs_key": needsKey, "has_key": hasKey.map { $0 as Any } ?? NSNull(),
            "model_entry": modelEntry,
            "listing": ["source": "", "error": ""],
            "models": [[String: Any]](),
        ]
    }

    // MARK: - fetching

    /// HTTP GET with a disk cache, so the list still shows offline. A fresh
    /// answer replaces the cache; a failed one falls back to it.
    struct Fetcher: Sendable {
        static var defaultCache: URL {
            FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("MeetOnTrack/stt-discovery", isDirectory: true)
        }

        let cache: URL
        let refresh: Bool
        var maxAge: TimeInterval = 24 * 3600
        var timeout: TimeInterval = 10

        func cacheFile(_ url: URL) -> URL {
            let name = url.absoluteString.unicodeScalars.map {
                CharacterSet.alphanumerics.contains($0) ? String($0) : "_"
            }.joined()
            return cache.appendingPathComponent(String(name.suffix(200)) + ".json")
        }

        func cached(_ url: URL) -> Data? { try? Data(contentsOf: cacheFile(url)) }

        func data(_ url: URL?) async -> (Data?, String?) {
            guard let url else { return (nil, "bad URL") }
            let file = cacheFile(url)
            if !refresh,
               let modified = (try? FileManager.default.attributesOfItem(atPath: file.path))?[.modificationDate] as? Date,
               Date().timeIntervalSince(modified) < maxAge,
               let data = try? Data(contentsOf: file) {
                return (data, nil)
            }
            var request = URLRequest(url: url)
            request.timeoutInterval = timeout
            do {
                let (data, response) = try await URLSession.shared.data(for: request)
                guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                    let code = (response as? HTTPURLResponse)?.statusCode ?? 0
                    return (cached(url), "HTTP \(code) for \(url.absoluteString)")
                }
                try? FileManager.default.createDirectory(at: cache, withIntermediateDirectories: true)
                try? data.write(to: file, options: .atomic)
                return (data, nil)
            } catch {
                // Stale beats nothing: the cache is the list as it last was.
                if let stale = cached(url) { return (stale, nil) }
                return (nil, "\(url.host ?? ""): \(error.localizedDescription)")
            }
        }

        func json(_ url: URL?) async -> (Any?, String?) {
            let (data, error) = await data(url)
            guard let data else { return (nil, error) }
            guard let json = try? JSONSerialization.jsonObject(with: data) else {
                return (nil, "unreadable JSON from \(url?.absoluteString ?? "")")
            }
            return (json, error)
        }

        /// OpenAI's model ids in the order returned. Not cached on disk: the
        /// list depends on the key, and the key is not something to key a
        /// cache file by.
        /// Model ids, with the name OpenAI gives one when its listing has one.
        func openAIModels(key: String) async -> ([(id: String, name: String?)]?, String?) {
            var request = URLRequest(url: URL(string: "https://api.openai.com/v1/models")!)
            request.setValue("Bearer \(key)", forHTTPHeaderField: "authorization")
            request.timeoutInterval = timeout
            do {
                let (data, response) = try await URLSession.shared.data(for: request)
                let code = (response as? HTTPURLResponse)?.statusCode ?? 0
                guard (200..<300).contains(code) else { return (nil, "HTTP \(code) from OpenAI") }
                let list = (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["data"]
                    as? [[String: Any]]
                return (list?.compactMap { item in
                    (item["id"] as? String).map { ($0, (item["display_name"] ?? item["name"]) as? String) }
                } ?? [], nil)
            } catch {
                return (nil, error.localizedDescription)
            }
        }
    }
}
