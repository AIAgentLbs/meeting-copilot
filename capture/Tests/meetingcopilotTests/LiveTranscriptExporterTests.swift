import Foundation
import Testing

@testable import meetingcopilot

struct LiveTranscriptExporterTests {
    @Test("Speaker evidence ends at the last decoded observation, not at meeting end")
    func observedSpeechEnd() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let path = root.appendingPathComponent("live.json")
        var state = LiveTranscriptState()
        let epoch = state.beginRecording(enabled: true)
        state.applyPartial(speaker: .them, text: "Hello", startMilliseconds: 1000, voiceID: 1, epoch: epoch)
        state.applyPartial(speaker: .them, text: "Hello again", startMilliseconds: 3000, voiceID: 1, epoch: epoch)
        state.finishRecording()
        let snapshot = LiveTranscriptionCoordinator.Snapshot(
            isRecording: false, isEnabled: false, entries: state.entries, status: .idle)
        let exporter = LiveTranscriptExporter(destination: path)
        await exporter.publish(snapshot, context: .init(
            meetingID: "synthetic-evidence", title: "Synthetic", startedAt: Date(timeIntervalSince1970: 0),
            remoteAttendees: [], meetingLink: nil, oneToOneRemoteSpeaker: nil))
        let json = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: path)) as? [String: Any])
        let segments = try #require(json["segments"] as? [[String: Any]])
        #expect(segments.first?["timestamp"] as? String == "1970-01-01T00:00:01Z")
        #expect(segments.first?["end_timestamp"] as? String == "1970-01-01T00:00:03Z")
        #expect(segments.first?["voice_id"] as? String == "remote-2")
    }
}
