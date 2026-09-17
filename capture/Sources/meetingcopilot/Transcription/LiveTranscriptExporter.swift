import Foundation

/// A deliberately small, local-only bridge from the in-memory live transcript
/// to the copilot UI. The file contains no audio or credentials
/// and is replaced atomically so readers never observe half-written JSON.
actor LiveTranscriptExporter {
    struct Context: Sendable {
        let meetingID: String
        let title: String
        let startedAt: Date
        let remoteAttendees: [String]
        let oneToOneRemoteSpeaker: String?
    }

    private struct Segment: Encodable {
        let source: String
        let timestamp: String
        let text: String
        let provisional: Bool
        let voiceID: String?
        let speaker: String?
        let speakerConfidence: String?

        enum CodingKeys: String, CodingKey {
            case source, timestamp, text, provisional
            case voiceID = "voice_id"
            case speaker
            case speakerConfidence = "speaker_confidence"
        }
    }

    private struct Payload: Encodable {
        let version: Int
        let source: String
        let meetingID: String
        let title: String
        let status: String
        let startedAt: String
        let updatedAt: String
        let remoteAttendees: [String]
        let segments: [Segment]

        enum CodingKeys: String, CodingKey {
            case version, source, title, status, segments
            case meetingID = "meeting_id"
            case startedAt = "started_at"
            case updatedAt = "updated_at"
            case remoteAttendees = "remote_attendees"
        }
    }

    private let destination: URL
    private let encoder: JSONEncoder

    init(destination: URL? = nil) {
        self.destination = destination
            ?? FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent(".local/share/meeting-copilot/meeting-copilot-live.json")
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        self.encoder = encoder
    }

    func publish(_ snapshot: LiveTranscriptionCoordinator.Snapshot, context: Context) {
        let now = Date()
        let segments = snapshot.entries.compactMap { entry -> Segment? in
            guard case .speech(let block) = entry else { return nil }
            return Segment(
                source: block.speaker == .you ? "microphone" : "system",
                timestamp: Self.iso(context.startedAt.addingTimeInterval(
                    Double(block.startMilliseconds) / 1000
                )),
                text: block.text,
                provisional: block.isProvisional,
                voiceID: block.voiceID.map { "remote-\($0 + 1)" },
                speaker: block.speaker == .them ? context.oneToOneRemoteSpeaker : nil,
                speakerConfidence: block.speaker == .them
                    && context.oneToOneRemoteSpeaker != nil
                    ? "calendar-one-on-one" : nil
            )
        }
        let payload = Payload(
            version: 1,
            source: "meeting-copilot",
            meetingID: context.meetingID,
            title: context.title,
            status: Self.status(snapshot),
            startedAt: Self.iso(context.startedAt),
            updatedAt: Self.iso(now),
            remoteAttendees: context.remoteAttendees,
            segments: segments
        )

        do {
            let parent = destination.deletingLastPathComponent()
            try FileManager.default.createDirectory(
                at: parent,
                withIntermediateDirectories: true,
                attributes: [.posixPermissions: 0o700]
            )
            let data = try encoder.encode(payload)
            try data.write(to: destination, options: .atomic)
            try FileManager.default.setAttributes(
                [.posixPermissions: 0o600], ofItemAtPath: destination.path)
        } catch {
            FileHandle.standardError.write(Data(
                "live transcript export failed: \(error)\n".utf8
            ))
        }
    }

    private static func status(_ snapshot: LiveTranscriptionCoordinator.Snapshot) -> String {
        guard snapshot.isRecording else { return "finished" }
        switch snapshot.status {
        case .idle: return "idle"
        case .paused: return "paused"
        case .loading: return "loading"
        case .live: return "recording"
        case .modelMissing: return "model_missing"
        case .overloaded: return "overloaded"
        case .error: return "error"
        }
    }

    private static func iso(_ date: Date) -> String {
        ISO8601DateFormatter().string(from: date)
    }
}
