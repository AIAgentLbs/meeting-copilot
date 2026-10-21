@preconcurrency import AVFoundation
import Foundation
import os.lock
import Testing

@testable import meetingcopilot

/// Opt-in, on-device acceptance. Generate public synthetic speech rather than
/// checking recordings or meeting text into Git. No model is downloaded here.
@Suite(.serialized)
struct LanguageRecognitionIntegrationTests {
    @Test("English audio is recognised as English",
          .enabled(if: ProcessInfo.processInfo.environment["MEETING_COPILOT_ASR_EN_FIXTURE"] != nil))
    func englishSpeech() async throws {
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

    /// Runs the live recognizer for the speech model chosen in Getting
    /// started: nothing here picks a model or a language.
    private func recognize(_ path: String) async throws -> String {
        guard case .ready(let choice) = Config.speechRecognition() else {
            Issue.record("choose a local speech model in Getting started before running acceptance")
            return ""
        }
        let recognizer = try await LiveModels.load(choice).recognizer(source: .system)
        let pulse = OSAllocatedUnfairLock(initialState: false)
        await recognizer.setPartialCallback { _ in pulse.withLock { $0 = true } }
        do {
            let file = try AVAudioFile(forReading: URL(fileURLWithPath: path))
            var silence = 0.0
            var committed: [String] = []
            while file.framePosition < file.length {
                let buffer = try #require(AVAudioPCMBuffer(
                    pcmFormat: file.processingFormat,
                    frameCapacity: AVAudioFrameCount(file.processingFormat.sampleRate)))
                try file.read(into: buffer)
                let seconds = Double(buffer.frameLength) / file.processingFormat.sampleRate
                try await recognizer.process(buffer)
                let spoke = pulse.withLock { value in
                    defer { value = false }
                    return value
                }
                silence = spoke ? 0 : silence + seconds
                if silence >= recognizer.pauseEndingUtterance {
                    committed.append(try await recognizer.finishUtterance())
                    silence = 0
                }
            }
            committed.append(try await recognizer.finishUtterance())
            await recognizer.cleanup()
            return committed.joined(separator: " ")
        } catch {
            await recognizer.cleanup()
            throw error
        }
    }
}
