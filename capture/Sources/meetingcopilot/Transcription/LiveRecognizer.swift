@preconcurrency import AVFoundation
import FluidAudio
import Foundation

/// One side's live recognizer, running the person's chosen model: Nemotron
/// ships stream natively; Parakeet runs through FluidAudio's sliding window.
/// Both report one running text per utterance through the callback.
protocol LiveRecognizer: Sendable {
    /// Audio without a decoded word that ends an utterance. A streaming model
    /// answers within a chunk, so a short pause is a real one; the sliding
    /// window answers a window at a time, so a pause has to outlast it.
    var pauseEndingUtterance: Double { get }
    func setPartialCallback(_ callback: @escaping @Sendable (String) -> Void) async
    func process(_ buffer: sending AVAudioPCMBuffer) async throws
    /// The utterance's final text; the next one starts from nothing.
    func finishUtterance() async throws -> String
    func cleanup() async
}

/// The heavyweight model files, loaded once per recording and shared by the
/// two sides.
enum LiveModels: @unchecked Sendable {
    case nemotron(SharedNemotronMultilingualModels, language: String)
    case parakeet(AsrModels)

    /// Why the chosen model cannot run live, or nil when it can.
    static func unavailableReason(_ choice: STTChoice) -> String? {
        guard choice.isLocal else { return STTCatalog.liveUnavailable }
        guard let model = LocalSTTModel.parse(choice.model) else {
            return "\(choice.model) is not a model the FluidAudio adapter can run"
        }
        guard model.isDownloaded else { return "\(choice.model) is not downloaded" }
        return nil
    }

    /// From disk only: a missing model is a status, never a download.
    static func load(_ choice: STTChoice) async throws -> LiveModels {
        if let reason = unavailableReason(choice) { throw STTRuntime.Failure(reason) }
        switch LocalSTTModel.parse(choice.model)! {
        case .nemotron(let ship):
            let shared = try await StreamingNemotronMultilingualAsrManager.preloadShared(
                from: LocalSTTModel.nemotron(ship: ship).directory)
            return .nemotron(shared, language: choice.language)
        case .parakeet(let version):
            return .parakeet(try await AsrModels.load(
                from: AsrModels.defaultCacheDirectory(for: version), version: version))
        }
    }

    func recognizer(source: AudioSource) async throws -> LiveRecognizer {
        switch self {
        case .nemotron(let shared, let language):
            let manager = StreamingNemotronMultilingualAsrManager()
            try await manager.loadFromShared(shared)
            await manager.setLanguage(language)
            return NemotronLiveRecognizer(manager: manager, language: language)
        case .parakeet(let models):
            return try await ParakeetLiveRecognizer.start(models: models, source: source)
        }
    }
}

struct NemotronLiveRecognizer: LiveRecognizer {
    let manager: StreamingNemotronMultilingualAsrManager
    let language: String
    var pauseEndingUtterance: Double { 2 }

    func setPartialCallback(_ callback: @escaping @Sendable (String) -> Void) async {
        await manager.setPartialCallback(callback)
    }

    func process(_ buffer: sending AVAudioPCMBuffer) async throws {
        _ = try await manager.process(audioBuffer: buffer)
    }

    /// finish() only empties the displayed token list; it keeps the decoder
    /// and language context. The next utterance starts afresh, in the chosen
    /// language, without reloading the models.
    func finishUtterance() async throws -> String {
        let final = try await manager.finish()
        await manager.reset()
        await manager.setLanguage(language)
        return final
    }

    func cleanup() async { await manager.cleanup() }
}

actor ParakeetLiveRecognizer: LiveRecognizer {
    private let manager: SlidingWindowAsrManager
    private var chunks: [String] = []
    private var callback: (@Sendable (String) -> Void)?
    private var updates: Task<Void, Never>?
    nonisolated let pauseEndingUtterance: Double

    private init(manager: SlidingWindowAsrManager, window: Double) {
        self.manager = manager
        pauseEndingUtterance = window
    }

    static func start(models: AsrModels, source: AudioSource) async throws -> ParakeetLiveRecognizer {
        let config = SlidingWindowAsrConfig.streaming
        let manager = SlidingWindowAsrManager(config: config)
        try await manager.loadModels(models)
        try await manager.startStreaming(source: source)
        let recognizer = ParakeetLiveRecognizer(
            manager: manager, window: config.chunkSeconds + config.rightContextSeconds)
        await recognizer.listen()
        return recognizer
    }

    private func listen() async {
        let stream = await manager.transcriptionUpdates
        updates = Task { [weak self] in
            for await update in stream { await self?.received(update.text) }
        }
    }

    /// Each update is one newly processed window; the utterance is all of
    /// them so far.
    private func received(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        chunks.append(trimmed)
        callback?(chunks.joined(separator: " "))
    }

    func setPartialCallback(_ callback: @escaping @Sendable (String) -> Void) async {
        self.callback = callback
    }

    func process(_ buffer: sending AVAudioPCMBuffer) async throws {
        await manager.streamAudio(buffer)
    }

    func finishUtterance() async throws -> String {
        let final = chunks.joined(separator: " ")
        chunks = []
        try await manager.reset()
        return final
    }

    func cleanup() async {
        updates?.cancel()
        await manager.cleanup()
    }
}
