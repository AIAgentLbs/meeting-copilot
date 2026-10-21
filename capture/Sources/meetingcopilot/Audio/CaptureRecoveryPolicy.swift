import Foundation

enum CaptureRecoveryPolicy {
    static func shouldRecover(
        now: Date, firstBufferAt: Date?, lastBufferAt: Date?, lastAudibleAt: Date?,
        outputChanged: Bool, callHasOutput: Bool, lastRecoveryAt: Date?, attempts: Int
    ) -> Bool {
        guard let firstBufferAt,
              lastRecoveryAt.map({ now.timeIntervalSince($0) >= 20 }) ?? true else { return false }
        if outputChanged { return true }
        if now.timeIntervalSince(lastBufferAt ?? firstBufferAt) >= 20 { return true }
        // Quiet alone is ambiguous — the far end may simply be silent — so it
        // alone spends the attempt budget. A tap that never carried sound
        // counts from its first buffer.
        return attempts < 3 && callHasOutput
            && now.timeIntervalSince(lastAudibleAt ?? firstBufferAt) >= 20
    }
}
