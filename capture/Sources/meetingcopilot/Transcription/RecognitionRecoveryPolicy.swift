import Foundation

enum LiveRecognitionStatus: Sendable, Equatable {
    case idle, paused, loading, live, modelMissing, overloaded
    case error(String)

    /// Queue pressure is recoverable only while the recorder keeps feeding it.
    var shouldDetachAudioSinks: Bool {
        if case .error = self { return true }
        return false
    }
}

/// Recognition is disposable; the recording and meeting identity are not.
/// Silence is healthy when audio is consumed. No words is not a stall.
struct RecognitionRecoveryPolicy: Sendable {
    enum Decision: Equatable { case healthy, wait, retry, exhausted }
    private(set) var attempts: [Date] = []
    static let stallAfter: TimeInterval = 40
    static let loadingGrace: TimeInterval = 120
    static let cooldown: TimeInterval = 90
    static let retryWindow: TimeInterval = 600
    static let maxAttempts = 3

    static func stalled(inputAt: Date?, consumedAt: Date?, now: Date) -> Bool {
        guard let inputAt, let consumedAt else { return false }
        return now.timeIntervalSince(inputAt) <= 15
            && now.timeIntervalSince(consumedAt) >= stallAfter
    }

    mutating func decide(needsRecovery: Bool, now: Date) -> Decision {
        guard needsRecovery else { return .healthy }
        attempts.removeAll { now.timeIntervalSince($0) >= Self.retryWindow }
        if let last = attempts.last, now.timeIntervalSince(last) < Self.cooldown {
            return .wait
        }
        guard attempts.count < Self.maxAttempts else { return .exhausted }
        attempts.append(now)
        return .retry
    }
}
