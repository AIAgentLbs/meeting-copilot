import EventKit
import Foundation

/// Reads the local calendars for two things: a real name for the session
/// folder instead of a bare timestamp, and a second, independent trigger for
/// automatic recording.
///
/// Opt-in (`auto_record.calendar`), because it costs a permission prompt and
/// because a calendar is only a good meeting signal if yours is accurate. The
/// mic-activity trigger needs no permission and no accurate calendar, so it
/// stays the default of the two.
@MainActor
final class CalendarWatcher {
    struct Meeting {
        let id: String
        let title: String
        let start: Date
        let end: Date
        let attendees: [String]
        /// Invitees other than the person whose calendar is being read. This
        /// makes a one-to-one call deterministic: every far-side transcript
        /// segment belongs to this one person even when acoustic diarization
        /// splits their voice into two labels.
        let remoteAttendees: [String]
        /// Conference link or location, whichever the event carries — kept so
        /// the recording folder can say where the call actually happened.
        let link: String?
        /// True when the event has other people or a conference link — the
        /// difference between a meeting and "dentist, 15:00".
        let looksLikeCall: Bool
    }

    private let store = EKEventStore()
    private let provider: String
    private(set) var authorized = false

    init(provider: String = Config.calendarProvider()) {
        self.provider = provider
    }

    /// Ask once, at startup, and only when the calendar trigger is enabled.
    /// Denial is not an error: the mic trigger carries on alone.
    func requestAccess() async {
        switch EKEventStore.authorizationStatus(for: .event) {
        case .fullAccess:
            authorized = true
        case .notDetermined:
            authorized = (try? await store.requestFullAccessToEvents()) ?? false
            if !authorized {
                FileHandle.standardError.write(Data(
                    "calendar access denied — auto-record falls back to mic activity only\n".utf8
                ))
            }
        default:
            authorized = false
            FileHandle.standardError.write(Data(
                "calendar access not granted — sessions will be named by time\n".utf8
            ))
        }
        if authorized && selectedCalendars().isEmpty {
            FileHandle.standardError.write(Data(
                "no \(provider) calendar source found — calendar context disabled\n".utf8
            ))
        }
        writePrivacySafeStatus()
    }

    /// Meetings that started within the last `window` seconds (or are about to,
    /// by up to 30s — calendar clocks and wall clocks disagree slightly) and
    /// look like calls. The auto-record trigger.
    func justStarted(now: Date, window: TimeInterval) -> [Meeting] {
        meetings(around: now, slack: window).filter {
            let sinceStart = now.timeIntervalSince($0.start)
            return sinceStart >= -30 && sinceStart <= window && $0.looksLikeCall
        }
    }

    /// The event that best describes a recording started at `date` — used to
    /// name the session folder even when the recording began some other way.
    /// Prefers something with other people in it over a solo block.
    func bestMatch(for date: Date) -> Meeting? {
        let candidates = meetings(around: date, slack: 8 * 60)
        return candidates.first { $0.looksLikeCall } ?? candidates.first
    }

    // MARK: -

    private func meetings(around date: Date, slack: TimeInterval) -> [Meeting] {
        guard authorized else { return [] }
        let calendars = selectedCalendars()
        guard !calendars.isEmpty else { return [] }

        let predicate = store.predicateForEvents(
            withStart: date.addingTimeInterval(-slack),
            end: date.addingTimeInterval(slack),
            calendars: calendars
        )
        return store.events(matching: predicate)
            .filter {
                !$0.isAllDay
                    && $0.status != .canceled
                    && !Self.currentUserDeclined($0)
            }
            .map(Self.convert)
            .sorted { lhs, rhs in
                let lhsContains = lhs.start <= date && date <= lhs.end
                let rhsContains = rhs.start <= date && date <= rhs.end
                if lhsContains != rhsContains { return lhsContains }
                if lhs.looksLikeCall != rhs.looksLikeCall { return lhs.looksLikeCall }
                return abs(lhs.start.timeIntervalSince(date))
                    < abs(rhs.start.timeIntervalSince(date))
            }
    }

    private func selectedCalendars() -> [EKCalendar] {
        let calendars = store.calendars(for: .event)
        guard provider == "google" else { return calendars }

        // EventKit has no Google provider enum. Depending on how the account
        // was added, the source title may be the account email, a generic
        // CalDAV label, or a localized title with no "google" marker at all.
        // Prefer positively identified Google sources, but fall back to every
        // non-Apple CalDAV source. The previous all-or-nothing identity check
        // returned zero calendars for a valid Google account.
        let nonApple = calendars.filter { calendar in
            guard let source = calendar.source else { return false }
            let identity = [source.title, source.sourceIdentifier]
                .joined(separator: " ")
                .lowercased()
            return !identity.contains("icloud") && !identity.contains("apple")
        }
        let markedGoogle = nonApple.filter { calendar in
            guard let source = calendar.source else { return false }
            let identity = [
                source.title, source.sourceIdentifier,
                calendar.title, calendar.calendarIdentifier,
            ].joined(separator: " ").lowercased()
            return identity.contains("google")
                || identity.contains("gmail")
                || identity.contains("@")
        }
        if !markedGoogle.isEmpty { return markedGoogle }
        return nonApple.filter { $0.source?.sourceType == .calDAV }
    }

    /// Publish only enough information for the local launcher/UI to explain
    /// whether calendar context is usable. Calendar names, account addresses,
    /// event titles and event contents never leave EventKit through this file.
    private func writePrivacySafeStatus() {
        let allCalendars = authorized ? store.calendars(for: .event) : []
        let matchingCalendars = authorized ? selectedCalendars() : []
        let payload: [String: Any] = [
            "version": 1,
            "provider": provider,
            "authorized": authorized,
            "matching_calendars": matchingCalendars.count,
            "total_event_calendars": allCalendars.count,
            "updated_at": ISO8601DateFormatter().string(from: Date()),
        ]

        let directory = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".config/meeting-copilot", isDirectory: true)
        let statusURL = directory.appendingPathComponent("calendar-status.json")

        do {
            try FileManager.default.createDirectory(
                at: directory,
                withIntermediateDirectories: true
            )
            var data = try JSONSerialization.data(
                withJSONObject: payload,
                options: [.prettyPrinted, .sortedKeys]
            )
            data.append(0x0A)
            try data.write(to: statusURL, options: .atomic)
            try FileManager.default.setAttributes(
                [.posixPermissions: 0o600],
                ofItemAtPath: statusURL.path
            )
        } catch {
            FileHandle.standardError.write(Data(
                "could not write privacy-safe calendar status: \(error)\n".utf8
            ))
        }
    }

    private static func convert(_ event: EKEvent) -> Meeting {
        let participants = event.attendees ?? []
        let label: (EKParticipant) -> String? = { participant in
            participant.name
                ?? participant.url.absoluteString
                    .replacingOccurrences(of: "mailto:", with: "")
        }
        let attendees = participants.compactMap(label)
        let remoteAttendees = participants.filter { !$0.isCurrentUser }.compactMap(label)
        let haystack = [
            event.location ?? "",
            event.url?.absoluteString ?? "",
            event.hasNotes ? (event.notes ?? "") : "",
        ].joined(separator: " ").lowercased()

        // The link is worth keeping verbatim; the notes are not — they are as
        // often a wall of boilerplate or something private as they are useful.
        let link = [event.url?.absoluteString, event.location]
            .compactMap { $0 }
            .first { !$0.trimmingCharacters(in: .whitespaces).isEmpty }

        return Meeting(
            id: event.eventIdentifier ?? UUID().uuidString,
            title: event.title ?? "meeting",
            start: event.startDate,
            end: event.endDate,
            attendees: attendees,
            remoteAttendees: remoteAttendees,
            link: link,
            looksLikeCall: !remoteAttendees.isEmpty
                || Self.conferenceMarkers.contains { haystack.contains($0) }
        )
    }

    private static func currentUserDeclined(_ event: EKEvent) -> Bool {
        (event.attendees ?? []).contains {
            $0.isCurrentUser && $0.participantStatus == .declined
        }
    }

    /// Substrings that mean "there's a call link in here". Kept broad rather
    /// than clever: a missed marker only costs the calendar trigger for that
    /// event, and the mic trigger still catches the meeting.
    private static let conferenceMarkers = [
        "zoom.us", "meet.google.com", "teams.microsoft", "teams.live", "whereby.com",
        "webex.com", "jitsi", "around.co", "gather.town", "huddle", "discord.gg",
        "telemost", "yandex.ru/telemost", "ktalk", "contour.ru", "salutejazz", "vkmeet",
    ]
}
