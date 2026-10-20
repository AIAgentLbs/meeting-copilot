import Foundation

enum CaptureRecoveryPolicy {
    static func shouldRecover(
        now: Date, firstBufferAt: Date?, lastBufferAt: Date?, lastNonzeroAt: Date?,
        outputChanged: Bool, callHasOutput: Bool, lastRecoveryAt: Date?, attempts: Int
    ) -> Bool {
        guard attempts < 3, let firstBufferAt,
              lastRecoveryAt.map({ now.timeIntervalSince($0) >= 60 }) ?? true else { return false }
        if outputChanged { return true }
        if now.timeIntervalSince(lastBufferAt ?? firstBufferAt) >= 20 { return true }
        return callHasOutput && lastNonzeroAt.map { now.timeIntervalSince($0) >= 45 } == true
    }
}
