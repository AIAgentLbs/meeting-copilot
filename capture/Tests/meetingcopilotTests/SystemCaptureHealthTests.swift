import Foundation
import Testing
@testable import meetingcopilot

struct SystemCaptureHealthTests {
    @Test func lostCaptureAndRouteChangesRecoverButNaturalSilenceDoesNotLoop() {
        let now = Date(timeIntervalSince1970: 1000)
        func decision(buffer: Double = 0, audible: Double? = 25,
                      route: Bool = false, playing: Bool = true,
                      retry: Double? = nil, attempts: Int = 0) -> Bool {
            SystemAudioRecorder.shouldRecover(
                now: now, firstBufferAt: now.addingTimeInterval(-100),
                lastBufferAt: now.addingTimeInterval(-buffer),
                lastAudibleAt: audible.map { now.addingTimeInterval(-$0) },
                outputChanged: route, callHasOutput: playing,
                lastRecoveryAt: retry.map { now.addingTimeInterval(-$0) }, attempts: attempts
            )
        }
        #expect(decision())
        #expect(decision(buffer: 25, audible: 10))
        #expect(decision(audible: 10, route: true))
        #expect(!decision(audible: nil))
        #expect(!decision(playing: false))
        #expect(!decision(audible: 10))
        #expect(!decision(retry: 10))
        #expect(!decision(attempts: 3))
    }

    /// The 2026-10-21 call: the tap kept delivering a −92 dBFS floor, which
    /// the old nonzero test (1e-5) counted as working capture for 39 minutes.
    @Test func faintFloorIsNotAudible() {
        #expect(Float(2.5e-5) < AudioLevel.audibleFloor)
        #expect(AudioLevel.audibleFloor < AudioLevel.speechThreshold)
    }
}
