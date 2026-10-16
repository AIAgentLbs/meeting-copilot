import FluidAudio

enum LiveUtteranceDecoder {
    /// finish() only empties the displayed token list; it retains the neural
    /// decoder and language context. A new utterance must start detection
    /// afresh, without unloading/reloading the heavyweight models.
    static func finish(_ manager: StreamingNemotronMultilingualAsrManager) async throws -> String {
        let final = try await manager.finish()
        await manager.reset()
        await manager.setLanguage("auto")
        return final
    }
}
