import Foundation
import Testing

@testable import meetingcopilot

/// A person reads a model by a name derived from the model's own metadata,
/// never by its id and never from a table of names.
struct STTDisplayNameTests {
    @Test("A local model reads as family, version and its languages")
    func localModels() {
        let v3 = LocalSTTModel.parakeet(.v3).id
        let twentyFive = (1...25).map { "l\($0)" }
        #expect(STTCatalog.displayName(v3, languages: twentyFive) == "Parakeet v3 (25 languages)")
        #expect(STTCatalog.displayName(v3, languages: twentyFive, in: .russian) == "Parakeet v3 (языков: 25)")
        #expect(STTCatalog.displayName(LocalSTTModel.parakeet(.tdtJa).id, languages: ["ja"])
            == "Parakeet 0.6B (Japanese)")
        #expect(STTCatalog.displayName(LocalSTTModel.parakeet(.tdtCtc110m).id, languages: nil) == "Parakeet 110M")
        let ship = LocalSTTModel.nemotron(ship: "latin/1120ms").id
        #expect(STTCatalog.displayName(ship, languages: ["en-US", "es-ES"])
            == "Nemotron 3.5, latin, 1120 ms (2 languages)")
    }

    @Test("Any other id is spelled out by the generic rule")
    func otherIds() {
        #expect(STTCatalog.displayName("gpt-4o-transcribe", languages: nil) == "Gpt 4o transcribe")
        #expect(STTCatalog.displayName("ls_eend_dih3_500ms", languages: nil) == "Ls eend dih3 500ms")
    }

    @Test("stt-options names the stored choice by its listing")
    func choiceName() {
        let engines: [[String: Any]] = [["id": "fluidaudio", "models": [["id": "m", "display_name": "M v1"]]]]
        #expect(STTCatalog.choiceName(["engine": "fluidaudio", "model": "m"], engines: engines) == "M v1")
        #expect(STTCatalog.choiceName(["engine": "openai", "model": "whisper-1"], engines: engines) == "Whisper 1")
        #expect(STTCatalog.choiceName(nil, engines: engines) == "")
    }
}
