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

/// One FluidAudio sliding-window manager per utterance: `finish()` drains
/// queued windows and flushes the incomplete one, and its input stream cannot
/// be reopened, so the next utterance gets a fresh manager on the same
/// loaded models.
actor ParakeetLiveRecognizer: LiveRecognizer {
    private let models: AsrModels
    private let source: AudioSource
    private let config = SlidingWindowAsrConfig.streaming
    private var manager: SlidingWindowAsrManager
    private var chunks: [String] = []
    private var callback: (@Sendable (String) -> Void)?
    private var updates: Task<Void, Never>?
    nonisolated let pauseEndingUtterance: Double

    private init(models: AsrModels, source: AudioSource, manager: SlidingWindowAsrManager) {
        self.models = models
        self.source = source
        self.manager = manager
        pauseEndingUtterance = SlidingWindowAsrConfig.streaming.chunkSeconds
            + SlidingWindowAsrConfig.streaming.rightContextSeconds
    }

    static func start(models: AsrModels, source: AudioSource) async throws -> ParakeetLiveRecognizer {
        let recognizer = ParakeetLiveRecognizer(
            models: models, source: source,
            manager: try await started(models: models, source: source))
        await recognizer.listen()
        return recognizer
    }

    private static func started(models: AsrModels, source: AudioSource) async throws -> SlidingWindowAsrManager {
        let manager = SlidingWindowAsrManager(config: .streaming)
        try await manager.loadModels(models)
        try await manager.startStreaming(source: source)
        return manager
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

    // ponytail: streamAudio only enqueues, so the coordinator's backlog limit
    // does not see a slow Parakeet decoder; bound it if live falls behind.
    func process(_ buffer: sending AVAudioPCMBuffer) async throws {
        await manager.streamAudio(buffer)
    }

    func finishUtterance() async throws -> String {
        let finished = manager
        let final = try await finished.finish()
        updates?.cancel()
        chunks = []
        await finished.cancel()
        manager = try await Self.started(models: models, source: source)
        await listen()
        return final.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    func cleanup() async {
        updates?.cancel()
        await manager.cleanup()
    }
}
