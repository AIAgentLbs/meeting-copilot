import Foundation
import Testing
@testable import meetingcopilot

struct SystemCaptureHealthTests {
    @Test func lostCaptureAndRouteChangesRecoverButNaturalSilenceDoesNotLoop() {
        let now = Date(timeIntervalSince1970: 1000)
        func decision(buffer: Double = 0, nonzero: Double? = 50,
                      route: Bool = false, playing: Bool = true,
                      retry: Double? = nil, attempts: Int = 0) -> Bool {
            SystemAudioRecorder.shouldRecover(
                now: now, firstBufferAt: now.addingTimeInterval(-100),
                lastBufferAt: now.addingTimeInterval(-buffer),
                lastNonzeroAt: nonzero.map { now.addingTimeInterval(-$0) },
                outputChanged: route, callHasOutput: playing,
                lastRecoveryAt: retry.map { now.addingTimeInterval(-$0) }, attempts: attempts
            )
        }
        #expect(decision())
        #expect(decision(buffer: 25, nonzero: 10))
        #expect(decision(nonzero: 10, route: true))
        #expect(!decision(nonzero: nil))
        #expect(!decision(playing: false))
        #expect(!decision(nonzero: 10))
        #expect(!decision(retry: 30))
        #expect(!decision(attempts: 3))
    }
}
