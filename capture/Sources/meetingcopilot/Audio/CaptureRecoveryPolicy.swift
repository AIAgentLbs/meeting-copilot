import Foundation

enum CaptureRecoveryPolicy {
    static func shouldRecover(
        now: Date, firstBufferAt: Date?, lastBufferAt: Date?, lastAudibleAt: Date?,
        outputChanged: Bool, callHasOutput: Bool, lastRecoveryAt: Date?, attempts: Int
    ) -> Bool {
        guard attempts < 3, let firstBufferAt,
              lastRecoveryAt.map({ now.timeIntervalSince($0) >= 20 }) ?? true else { return false }
        if outputChanged { return true }
        if now.timeIntervalSince(lastBufferAt ?? firstBufferAt) >= 20 { return true }
        // A tap that never carried sound counts from its first buffer; the
        // attempt cap keeps a call that starts in silence from looping.
        return callHasOutput && now.timeIntervalSince(lastAudibleAt ?? firstBufferAt) >= 20
    }
}
