@preconcurrency import AVFoundation
import FluidAudio
import Foundation
import os.lock
import Testing

@testable import meetingcopilot

/// Opt-in, on-device acceptance. Generate public synthetic speech rather than
/// checking recordings or meeting text into Git. No model is downloaded here.
@Suite(.serialized)
struct LanguageRecognitionIntegrationTests {
    @Test("English audio stays English with a Russian meeting preference",
          .enabled(if: ProcessInfo.processInfo.environment["MEETING_COPILOT_ASR_EN_FIXTURE"] != nil))
    func englishWithRussianPreference() async throws {
        let fixture = try #require(ProcessInfo.processInfo.environment["MEETING_COPILOT_ASR_EN_FIXTURE"])
        let text = try await recognize(fixture)
        let words = Set(text.lowercased().split { !$0.isLetter }.map(String.init))
        #expect(words.contains("project"))
        #expect(words.contains("meeting"))
        #expect(words.contains("schedule"))
    }

    @Test("Mixed English and Russian audio preserves both languages",
          .enabled(if: ProcessInfo.processInfo.environment["MEETING_COPILOT_ASR_MIXED_FIXTURE"] != nil))
    func mixedSpeech() async throws {
        let fixture = try #require(ProcessInfo.processInfo.environment["MEETING_COPILOT_ASR_MIXED_FIXTURE"])
        let text = try await recognize(fixture)
        let words = Set(text.lowercased().split { !$0.isLetter }.map(String.init))
        #expect(words.contains("project"))
        #expect(words.contains("meeting"))
        #expect(words.contains("встреча"))
        #expect(words.contains("результаты"))
    }

    @Test("English, Russian and Spanish switches stay in their spoken languages",
          .enabled(if: ProcessInfo.processInfo.environment["MEETING_COPILOT_ASR_THREE_FIXTURE"] != nil))
    func threeLanguages() async throws {
        let fixture = try #require(ProcessInfo.processInfo.environment["MEETING_COPILOT_ASR_THREE_FIXTURE"])
        try await checkThreeLanguages(fixture)
    }

    @Test("Utterance pauses reset detection before the next language",
          .enabled(if: ProcessInfo.processInfo.environment["MEETING_COPILOT_ASR_THREE_PAUSED_FIXTURE"] != nil))
    func threeLanguagesWithPauses() async throws {
        let fixture = try #require(ProcessInfo.processInfo.environment["MEETING_COPILOT_ASR_THREE_PAUSED_FIXTURE"])
        try await checkThreeLanguages(fixture)
    }

    private func checkThreeLanguages(_ fixture: String) async throws {
        let text = try await recognize(fixture)
        let words = Set(text.lowercased().split { !$0.isLetter }.map(String.init))
        #expect(words.contains("project"))
        #expect(words.contains("встреча"))
        #expect(words.contains("результаты"))
        #expect(words.contains("proyecto"))
        #expect(words.contains("reunión"))
    }

    private func recognize(_ path: String) async throws -> String {
        let language = LiveTranscriptionLanguage.prompt(for: "ru")
        let store = LiveTranscriptionModelStore()
        try #require(store.isReady(language: language), "Install the multilingual live model before running acceptance")
        let manager = StreamingNemotronMultilingualAsrManager()
        try await manager.loadModels(from: store.variantDirectory(language: language))
        await manager.setLanguage(language)
        let pulse = OSAllocatedUnfairLock(initialState: false)
        await manager.setPartialCallback { _ in pulse.withLock { $0 = true } }
        do {
            let file = try AVAudioFile(forReading: URL(fileURLWithPath: path))
            let converter = AudioConverter()
            var silence = 0.0
            var committed: [String] = []
            while file.framePosition < file.length {
                let buffer = try #require(AVAudioPCMBuffer(
                    pcmFormat: file.processingFormat,
                    frameCapacity: AVAudioFrameCount(file.processingFormat.sampleRate)))
                try file.read(into: buffer)
                let samples = try converter.resampleBuffer(buffer)
                _ = try await manager.process(samples: samples)
                let spoke = pulse.withLock { value in
                    defer { value = false }
                    return value
                }
                silence = spoke ? 0 : silence + Double(samples.count) / 16000
                if silence >= 2 {
                    committed.append(try await LiveUtteranceDecoder.finish(manager))
                    silence = 0
                }
            }
            committed.append(try await manager.finish())
            await manager.cleanup()
            return committed.joined(separator: " ")
        } catch {
            await manager.cleanup()
            throw error
        }
    }
}
