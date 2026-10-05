@preconcurrency import AVFoundation
import CoreAudio
import Foundation
import os.lock

/// Records system audio output to a file via a Core Audio process tap
/// (macOS 14.2+). No virtual device, no kernel extension — the tap mixes the
/// chosen processes' output to stereo and hands us buffers through a private
/// aggregate device. First use triggers the one-time "System Audio Recording"
/// TCC prompt and lights the purple recording indicator while active.
final class SystemAudioRecorder {
    /// Whose output lands on the far-end track.
    enum Scope: Equatable {
        /// Everything the Mac plays. Safe and indiscriminate: notification
        /// dings, music and the video you opened afterwards all count as "the
        /// meeting", both in the transcript and in the auto-record loop's
        /// judgement of whether anyone is still talking.
        case everything
        /// Only processes belonging to these bundle-id families — the call
        /// app. Cleaner recordings, and a far-end silence signal that means
        /// what it says.
        case apps([String])
    }

    enum RecorderError: Error, CustomStringConvertible {
        case tapCreationFailed(OSStatus)
        case tapFormatUnreadable(OSStatus)
        case aggregateCreationFailed(OSStatus)
        case ioProcCreationFailed(OSStatus)
        case deviceStartFailed(OSStatus)
        case fileCreationFailed(Error)

        var description: String {
            switch self {
            case .tapCreationFailed(let s):
                return "process tap creation failed (OSStatus \(s)) — check System Settings → Privacy & Security → Screen & System Audio Recording"
            case .tapFormatUnreadable(let s): return "couldn't read tap stream format (OSStatus \(s))"
            case .aggregateCreationFailed(let s): return "aggregate device creation failed (OSStatus \(s))"
            case .ioProcCreationFailed(let s): return "IO proc creation failed (OSStatus \(s))"
            case .deviceStartFailed(let s): return "device start failed (OSStatus \(s))"
            case .fileCreationFailed(let e): return "output file creation failed: \(e)"
            }
        }
    }

    private(set) var scope: Scope = .everything
    /// The audio objects currently in the tap. Compared on refresh so a tap is
    /// only rewritten when the app's set of processes has actually changed.
    private var tappedObjects: [AudioObjectID] = []
    private var refreshFailed = false

    private var tapID = AudioObjectID(kAudioObjectUnknown)
    private var aggregateID = AudioObjectID(kAudioObjectUnknown)
    private var procID: AudioDeviceIOProcID?
    private let queue = DispatchQueue(label: "com.aiagentlabs.meeting-copilot.system-tap")
    private let liveAudio = LiveAudioBufferRelay()
    private(set) var isRecording = false
    private var outputDevice: AudioObjectID?
    private var lastRecoveryAt: Date?
    private var recoveryAttempts = 0
    private(set) var recoveryEvents: [[String: String]] = []
    private var converter: AVAudioConverter?

    // Thread-safe shared state: accessed from both the main thread and the
    // IOProc callback (background serial queue) without further sync.
    // Every access is serialized by OSAllocatedUnfairLock. AVAudioFile itself
    // is not Sendable, so the lock is the synchronization boundary.
    private struct LockedState: @unchecked Sendable {
        var file: AVAudioFile?
        var firstBufferAt: Date?
        var lastSoundAt: Date?
        var levelMeasurable = true
        var bufferCount = 0
        var highestPeak: Float = 0
        var lastBufferAt: Date?
        var lastNonzeroAt: Date?
        var muted = false
    }
    private let state = OSAllocatedUnfairLock(initialState: LockedState())

    /// Wall-clock time of the last buffer louder than the noise floor — the
    /// far end saying something. nil means nothing audible yet.
    var lastSoundAt: Date? { state.withLock { $0.lastSoundAt } }

    /// False once a buffer arrived in a sample format we can't measure.
    var levelMeasurable: Bool { state.withLock { $0.levelMeasurable } }

    /// A process tap can start successfully yet return zeroes forever when its
    /// privacy grant is missing. File growth cannot distinguish that failure.
    func isDigitallySilent(now: Date = Date()) -> Bool {
        state.withLock { s in
            guard s.levelMeasurable else { return false }
            return Self.isDigitallySilent(
                firstBufferAt: s.firstBufferAt,
                bufferCount: s.bufferCount,
                highestPeak: s.highestPeak,
                now: now
            )
        }
    }

    static func isDigitallySilent(
        firstBufferAt: Date?,
        bufferCount: Int,
        highestPeak: Float,
        now: Date,
        grace: TimeInterval = 10
    ) -> Bool {
        guard let firstBufferAt, bufferCount > 0 else { return false }
        return now.timeIntervalSince(firstBufferAt) >= grace && highestPeak == 0
    }

    /// While muted the tap keeps running and silence is written instead of the
    /// audio, so the track stays wall-clock aligned across a pause.
    var isMuted: Bool {
        get { state.withLock { $0.muted } }
        set { state.withLock { $0.muted = newValue } }
    }

    private var file: AVAudioFile? {
        get { state.withLock { $0.file } }
        set { state.withLock { $0.file = newValue } }
    }

    /// Wall-clock time of the first captured buffer — the track's true start,
    /// used to offset-align the two tracks' transcript timestamps.
    private(set) var firstBufferAt: Date? {
        get { state.withLock { $0.firstBufferAt } }
        set { state.withLock { $0.firstBufferAt = newValue } }
    }

    /// Start capturing system audio as PCM in `url` (use a .caf extension —
    /// CAF needs no finalization pass, so a crash mid-meeting loses nothing
    /// already written).
    func start(writingTo url: URL, scope: Scope = .everything) throws {
        guard !isRecording else { return }

        let (description, objects) = Self.describe(scope)
        self.scope = objects.isEmpty ? .everything : scope
        tappedObjects = objects

        var newTapID = AudioObjectID(kAudioObjectUnknown)
        let status = AudioHardwareCreateProcessTap(description, &newTapID)
        guard status == noErr else { throw RecorderError.tapCreationFailed(status) }
        tapID = newTapID

        do {
            let format = try tapStreamFormat()
            try createAggregateDevice(tapUUID: description.uuid)
            file = try makeFile(url: url, format: format)
            try installIOProc(format: format)
        } catch {
            cleanup()
            throw error
        }

        isRecording = true
        outputDevice = AudioDevices.defaultOutput()
    }

    /// File growth is not proof of capture: a dead tap can keep writing zeroes.
    /// Rebuild on an output-route change, stalled callbacks, or sustained
    /// digital silence while a call process is still playing. Preserve the
    /// open file, installed live sink and clock; never truncate earlier audio.
    func checkHealth(now: Date = Date(), callHasOutput: Bool) {
        guard isRecording, let outputFile = file else { return }
        let currentOutput = AudioDevices.defaultOutput()
        let signal = state.withLock { ($0.lastBufferAt, $0.lastNonzeroAt, $0.muted) }
        guard !signal.2 else { return }
        if let recovered = lastRecoveryAt, let nonzero = signal.1, nonzero > recovered {
            recoveryAttempts = 0
        }
        guard Self.shouldRecover(
            now: now, firstBufferAt: firstBufferAt, lastBufferAt: signal.0,
            lastNonzeroAt: signal.1, outputChanged: currentOutput != outputDevice,
            callHasOutput: callHasOutput, lastRecoveryAt: lastRecoveryAt,
            attempts: recoveryAttempts
        ) else { return }
        recoveryAttempts += 1
        lastRecoveryAt = now
        outputDevice = currentOutput
        if let procID { AudioDeviceStop(aggregateID, procID) }
        cleanup(preserveFile: true)
        do {
            let (description, objects) = Self.describe(scope)
            var newTap = AudioObjectID(kAudioObjectUnknown)
            let status = AudioHardwareCreateProcessTap(description, &newTap)
            guard status == noErr else { throw RecorderError.tapCreationFailed(status) }
            tapID = newTap
            tappedObjects = objects
            let format = try tapStreamFormat()
            converter = format == outputFile.processingFormat ? nil
                : AVAudioConverter(from: format, to: outputFile.processingFormat)
            if format != outputFile.processingFormat && converter == nil {
                throw RecorderError.tapFormatUnreadable(-1)
            }
            try createAggregateDevice(tapUUID: description.uuid)
            // Account for the capture gap before resumed audio, not at EOF.
            if let start = firstBufferAt {
                let missing = Int64(Date().timeIntervalSince(start) * outputFile.processingFormat.sampleRate) - outputFile.length
                if missing > 0, missing < Int64(outputFile.processingFormat.sampleRate * 120),
                   let pad = AVAudioPCMBuffer(pcmFormat: outputFile.processingFormat, frameCapacity: AVAudioFrameCount(missing)) {
                    pad.frameLength = AVAudioFrameCount(missing)
                    if let silence = AudioLevel.silence(like: pad) { try outputFile.write(from: silence) }
                }
            }
            try installIOProc(format: format)
            recoveryEvents.append(["at": ISO8601DateFormatter().string(from: now), "status": "restarted"])
            FileHandle.standardError.write(Data("system tap rebuilt after capture/route loss\n".utf8))
        } catch {
            cleanup(preserveFile: true)
            recoveryEvents.append(["at": ISO8601DateFormatter().string(from: now), "status": "failed", "error": String(describing: error)])
            FileHandle.standardError.write(Data("system tap recovery failed: \(error)\n".utf8))
        }
    }

    static func shouldRecover(
        now: Date, firstBufferAt: Date?, lastBufferAt: Date?, lastNonzeroAt: Date?,
        outputChanged: Bool, callHasOutput: Bool, lastRecoveryAt: Date?, attempts: Int
    ) -> Bool {
        CaptureRecoveryPolicy.shouldRecover(
            now: now, firstBufferAt: firstBufferAt, lastBufferAt: lastBufferAt,
            lastNonzeroAt: lastNonzeroAt, outputChanged: outputChanged,
            callHasOutput: callHasOutput, lastRecoveryAt: lastRecoveryAt, attempts: attempts
        )
    }

    /// Stop capturing and finalize the file. Idempotent.
    func stop() {
        guard isRecording else { return }
        isRecording = false
        if let procID, aggregateID != kAudioObjectUnknown {
            AudioDeviceStop(aggregateID, procID)
        }
        cleanup()
        liveAudio.install(nil)
    }

    func installLiveAudioSink(_ sink: LiveAudioBufferRelay.Sink?) {
        liveAudio.install(sink)
    }

    func setLiveAudioPaused(_ paused: Bool) {
        liveAudio.isPaused = paused
    }

    /// Re-point the tap at the app's processes as they come and go — a
    /// browser renderer restarted by a reloaded tab, a helper the call app
    /// spawns when someone shares their screen, or a second call app joining
    /// the session. Cheap enough for the 15-second liveness tick.
    ///
    /// The tap's description is settable, so this never touches the aggregate
    /// device or the file — nothing about the recording is interrupted. If the
    /// system refuses, the existing tap keeps running and we say so once
    /// rather than every fifteen seconds for an hour.
    func refresh(scope newScope: Scope) {
        guard isRecording, tapID != kAudioObjectUnknown else { return }
        guard case .apps = newScope else { return }

        let (description, objects) = Self.describe(newScope)
        guard !objects.isEmpty, objects != tappedObjects else { return }

        var address = AudioObjectPropertyAddress(
            mSelector: kAudioTapPropertyDescription,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var value = description
        let status = withUnsafeMutablePointer(to: &value) { pointer in
            AudioObjectSetPropertyData(
                tapID, &address, 0, nil, UInt32(MemoryLayout<CATapDescription>.size), pointer
            )
        }
        guard status == noErr else {
            if !refreshFailed {
                refreshFailed = true
                FileHandle.standardError.write(Data(
                    ("system tap: can't update the tapped processes (OSStatus \(status)) — "
                        + "keeping the ones it started with\n").utf8
                ))
            }
            return
        }
        tappedObjects = objects
        scope = newScope
        FileHandle.standardError.write(Data(
            "system tap: now following \(objects.count) process(es)\n".utf8
        ))
    }

    // MARK: -

    /// Build a tap description for a scope, plus the audio objects it covers.
    /// An app scope that matches no running process comes back as a global tap
    /// — recording everything is wrong in a small way, recording nothing is
    /// wrong in the way that loses the meeting.
    private static func describe(_ scope: Scope) -> (CATapDescription, [AudioObjectID]) {
        var objects: [AudioObjectID] = []
        var bundleIDs: [String] = []
        if case .apps(let families) = scope {
            let processes = AudioProcesses.matching(families: families)
            objects = processes.map(\.object)
            bundleIDs = Array(Set(processes.map(\.bundleID))).sorted()
            if objects.isEmpty {
                FileHandle.standardError.write(Data(
                    ("system tap: nothing running for \(families.joined(separator: ", ")) — "
                        + "recording all system audio instead\n").utf8
                ))
            }
        }

        let description = objects.isEmpty
            ? CATapDescription(stereoGlobalTapButExcludeProcesses: [])
            : CATapDescription(stereoMixdownOfProcesses: objects)
        description.name = "meetingcopilot system tap"
        description.isPrivate = true
        description.muteBehavior = .unmuted

        if !objects.isEmpty, #available(macOS 26.0, *) {
            // Ask the system to keep following these apps across restarts: a
            // call app that relaunches mid-meeting otherwise drops out of the
            // tap silently, and a silent far-end track is the failure this
            // program exists to avoid.
            description.bundleIDs = bundleIDs
            description.isProcessRestoreEnabled = true
        }
        return (description, objects)
    }

    private func tapStreamFormat() throws -> AVAudioFormat {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioTapPropertyFormat,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var asbd = AudioStreamBasicDescription()
        var size = UInt32(MemoryLayout<AudioStreamBasicDescription>.size)
        let status = AudioObjectGetPropertyData(tapID, &address, 0, nil, &size, &asbd)
        guard status == noErr, let format = AVAudioFormat(streamDescription: &asbd) else {
            throw RecorderError.tapFormatUnreadable(status)
        }
        return format
    }

    private func createAggregateDevice(tapUUID: UUID) throws {
        let desc: [String: Any] = [
            kAudioAggregateDeviceNameKey: "meetingcopilot-tap",
            kAudioAggregateDeviceUIDKey: UUID().uuidString,
            kAudioAggregateDeviceIsPrivateKey: true,
            kAudioAggregateDeviceIsStackedKey: false,
            kAudioAggregateDeviceTapAutoStartKey: true,
            kAudioAggregateDeviceSubDeviceListKey: [] as [[String: Any]],
            kAudioAggregateDeviceTapListKey: [
                [
                    kAudioSubTapUIDKey: tapUUID.uuidString,
                    kAudioSubTapDriftCompensationKey: true,
                ]
            ],
        ]
        var newAggregateID = AudioObjectID(kAudioObjectUnknown)
        let status = AudioHardwareCreateAggregateDevice(desc as CFDictionary, &newAggregateID)
        guard status == noErr else { throw RecorderError.aggregateCreationFailed(status) }
        aggregateID = newAggregateID
    }

    private func makeFile(url: URL, format: AVAudioFormat) throws -> AVAudioFile {
        do {
            return try AVAudioFile(
                forWriting: url,
                settings: AudioFormats.pcmSettings(
                    sampleRate: format.sampleRate, channels: format.channelCount
                ),
                commonFormat: format.commonFormat,
                interleaved: format.isInterleaved
            )
        } catch {
            throw RecorderError.fileCreationFailed(error)
        }
    }

    private func installIOProc(format: AVAudioFormat) throws {
        var status = AudioDeviceCreateIOProcIDWithBlock(&procID, aggregateID, queue) {
            [weak self] _, inInputData, _, _, _ in
            guard let self, let file = self.file else { return }
            if self.firstBufferAt == nil { self.firstBufferAt = Date() }
            guard let buffer = AVAudioPCMBuffer(
                pcmFormat: format,
                bufferListNoCopy: inInputData,
                deallocator: nil
            ) else { return }
            self.writeTracked(buffer, to: file)
        }
        guard status == noErr, let procID else { throw RecorderError.ioProcCreationFailed(status) }

        status = AudioDeviceStart(aggregateID, procID)
        guard status == noErr else { throw RecorderError.deviceStartFailed(status) }
    }

    /// Write one tapped buffer, tracking its level on the way through and
    /// substituting silence while paused.
    private func writeTracked(_ buffer: AVAudioPCMBuffer, to file: AVAudioFile) {
        let peak = AudioLevel.peak(of: buffer)
        let muted: Bool = state.withLock { s in
            s.bufferCount += 1
            s.lastBufferAt = Date()
            if let peak {
                if peak > 0.00001 { s.lastNonzeroAt = Date() }
                s.highestPeak = max(s.highestPeak, peak)
                if peak >= AudioLevel.speechThreshold { s.lastSoundAt = Date() }
            } else {
                s.levelMeasurable = false
            }
            return s.muted
        }

        var outgoing = buffer
        if muted {
            // The tap's buffer is Core Audio's memory, borrowed no-copy — the
            // silence has to be written into a buffer of our own.
            guard let silent = AudioLevel.silence(like: buffer) else { return }
            outgoing = silent
        }
        do {
            if let converter {
                let capacity = AVAudioFrameCount(ceil(Double(outgoing.frameLength) * file.processingFormat.sampleRate / outgoing.format.sampleRate)) + 32
                guard let converted = AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: capacity) else { return }
                let input = ConversionInput(buffer: outgoing)
                var error: NSError?
                converter.convert(to: converted, error: &error) { _, status in
                    guard input.take() else { status.pointee = .noDataNow; return nil }
                    status.pointee = .haveData
                    return input.buffer
                }
                if let error { throw error }
                try file.write(from: converted)
            } else {
                try file.write(from: outgoing)
            }
            liveAudio.forward(outgoing)
        } catch {
            FileHandle.standardError.write(Data("system track write failed: \(error)\n".utf8))
        }
    }

    private func cleanup(preserveFile: Bool = false) {
        if let procID, aggregateID != kAudioObjectUnknown {
            AudioDeviceDestroyIOProcID(aggregateID, procID)
        }
        procID = nil
        if aggregateID != kAudioObjectUnknown {
            AudioHardwareDestroyAggregateDevice(aggregateID)
            aggregateID = AudioObjectID(kAudioObjectUnknown)
        }
        if tapID != kAudioObjectUnknown {
            AudioHardwareDestroyProcessTap(tapID)
            tapID = AudioObjectID(kAudioObjectUnknown)
        }
        converter = nil
        if !preserveFile { file = nil }
    }

    private final class ConversionInput: @unchecked Sendable {
        let buffer: AVAudioPCMBuffer
        private let supplied = OSAllocatedUnfairLock(initialState: false)
        init(buffer: AVAudioPCMBuffer) { self.buffer = buffer }
        func take() -> Bool {
            supplied.withLock { used in
                guard !used else { return false }
                used = true
                return true
            }
        }
    }
}
