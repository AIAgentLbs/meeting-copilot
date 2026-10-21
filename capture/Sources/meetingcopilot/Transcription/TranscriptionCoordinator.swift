import Foundation

/// Post-recording pipeline: a serial queue of session folders to transcribe.
///
/// Per-track engines (parakeet) get mic.caf → "me" and system.caf → "them";
/// each track's segments are shifted by its start offset and merged by
/// timestamp. AssemblyAI gets aligned stereo and returns channel-qualified
/// speaker labels. Mixed engines still get one mixed.m4a and map anonymous
/// labels back onto me/them from the source tracks' energy.
///
/// Either way the result is transcript.json (canonical) plus transcript.md
/// (readable). The filesystem is the queue —
/// `resumePending()` rescans at launch, so a crash or quit mid-transcription
/// just retries on next run. Failures append to the session's transcribe.log
/// and never block later jobs.
actor TranscriptionCoordinator {
    enum Status: Sendable {
        case idle
        case transcribing(session: String, queued: Int)
        case failed(session: String)
    }

    /// The single mixed-down file used by engines that cannot consume the two
    /// channels directly. Derived from the tracks and regenerated when absent.
    private static let mixedFile = "mixed.m4a"
    private static let multichannelFile = "multichannel.m4a"
    private static let multichannelTemporary = "multichannel.tmp.m4a"

    /// How many times a session may fail before the queue stops offering it.
    /// The queue lives in the filesystem and is rescanned at every launch, so
    /// without a limit a session that cannot be transcribed is retried for
    /// ever — and with a cloud engine, re-uploaded and re-charged every time.
    private static let maxAttempts = 3

    private var queue: [URL] = []
    private var draining = false
    private var engine: TranscriptionEngine?
    /// The choice `engine` was built for, so a changed choice gets a new one.
    private var engineChoice: STTChoice?
    private var lastFailure: String?
    private var statusHandler: (@Sendable (Status) -> Void)?

    /// An engine settled on in advance rather than chosen for the machine at
    /// the moment there is work. Only tests pass one: everything real wants
    /// the configured answer, and wants it decided late.
    private let fixedEngine: TranscriptionEngine?
    private let onStop: @Sendable () -> String?
    /// The stored speech choice; tests pass their own.
    private let resolve: @Sendable () -> STTResolution

    init(engine: TranscriptionEngine? = nil,
         onStop: @escaping @Sendable () -> String? = { Config.onStop() },
         resolve: @escaping @Sendable () -> STTResolution = { Config.speechRecognition() }) {
        fixedEngine = engine
        self.onStop = onStop
        self.resolve = resolve
    }

    func setStatusHandler(_ handler: @escaping @Sendable (Status) -> Void) {
        statusHandler = handler
    }

    /// Queue a finished session. With transcription disabled in config, the
    /// on_stop hook still fires — it just gets an untranscribed folder.
    func enqueue(_ sessionDir: URL) {
        guard Config.transcriptionEnabled() else {
            Task {
                do { try await archiveRecordingOnly(sessionDir) }
                catch { log(sessionDir, "recording-only archive deferred: \(error)") }
            }
            return
        }
        queue.append(sessionDir)
        drainIfIdle()
    }

    /// With no transcript the audio is the only copy of the meeting. Archive
    /// it regardless of keep_audio, under the same claim as transcription.
    func archiveRecordingOnly(_ dir: URL) async throws {
        try SessionClaim.acquire(dir, stage: .transcribe)
        await Task.detached(priority: .utility) { TrackCompressor.compress(sessionDir: dir) }.value
        SessionClaim.release(dir)
        runHook(for: dir)
    }

    /// Scan the recordings root for sessions that finished (meta.json exists)
    /// but were never transcribed. Folder names sort chronologically, so
    /// oldest-first is a name sort.
    func resumePending(root: URL) {
        guard Config.transcriptionEnabled() else { return }
        let pending = Self.pendingSessions(in: root)
        for dir in pending where !queue.contains(dir) {
            queue.append(dir)
        }
        if !pending.isEmpty {
            FileHandle.standardError.write(Data(
                "resuming \(pending.count) untranscribed session(s)\n".utf8
            ))
        }
        drainIfIdle()
    }

    /// The folders `resumePending` would take, as a plain question about a
    /// directory: which sessions have ended, have no transcript, have not been
    /// retired, and are not being worked on by somebody else. Separate from the
    /// queueing so the answer can be checked without a coordinator running a
    /// drain over real audio.
    static func pendingSessions(in root: URL) -> [URL] {
        guard let entries = try? FileManager.default.contentsOfDirectory(
            at: root, includingPropertiesForKeys: nil
        ) else { return [] }

        let fm = FileManager.default
        return entries
            .filter {
                fm.fileExists(atPath: $0.appendingPathComponent("meta.json").path)
                    && !fm.fileExists(atPath: $0.appendingPathComponent("transcript.json").path)
                    && !hasGivenUp(on: $0)
                    // A session another process is already transcribing is not
                    // pending, it is in progress somewhere else. Queueing it
                    // would be refused at the claim anyway; leaving it out is
                    // what stops the menu bar counting somebody else's work as
                    // its own backlog.
                    && !SessionClaim.isHeld($0)
            }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
    }

    // MARK: -

    private func drainIfIdle() {
        guard !draining, !queue.isEmpty else { return }
        draining = true
        lastFailure = nil
        Task { await drain() }
    }

    private func drain() async {
        while !queue.isEmpty {
            let dir = queue.removeFirst()
            publish(.transcribing(session: dir.lastPathComponent, queued: queue.count))
            do {
                try await transcribeAndAnnounce(dir)
            } catch let busy as SessionClaim.Busy {
                // Not a failure of this session — a collision with another
                // process that has it. Counting it would retire a perfectly
                // good recording after three unlucky launches, so the folder is
                // simply left where it is: the filesystem is the queue, and the
                // next `resumePending` offers it again once the owner is done.
                log(dir, "\(busy)")
            } catch let deferred as TranscriptionDeferred {
                recordDeferred(deferred, for: dir)
            } catch {
                log(dir, "transcription failed: \(error)")
                lastFailure = dir.lastPathComponent
                recordFailure(error, for: dir)
            }
        }
        await releaseEngine()
        publish(lastFailure.map { .failed(session: $0) } ?? .idle)
        draining = false
        // An enqueue that landed between the loop exiting and the release
        // finishing would otherwise sit until the next enqueue.
        drainIfIdle()
    }

    /// Transcribe one session now, and wait for it.
    ///
    /// `enqueue` belongs to the running app: it hands work to a queue, reports
    /// through the menu bar, and leaves a failure in transcribe.log for
    /// whoever looks. `meetingcopilot process` has a person and a terminal instead, so
    /// it wants the failure back to print and to exit on. The work is the same
    /// either way, down to pulling one channel out of `audio.m4a` — a settled
    /// session has nothing else left to transcribe from.
    ///
    /// `override` is a one-run speech choice (`process --again --engine …`):
    /// checked like the stored one, used for this run only, never saved.
    func transcribeNow(_ dir: URL, override: STTChoice? = nil) async throws {
        do {
            try await transcribeAndAnnounce(dir, override: override)
        } catch let busy as SessionClaim.Busy {
            // The app has this session. Nothing failed, so nothing is recorded
            // against it — the person gets the sentence and the folder is left
            // exactly as the process that owns it expects to find it.
            log(dir, "\(busy)")
            await releaseEngine()
            throw busy
        } catch let deferred as TranscriptionDeferred {
            recordDeferred(deferred, for: dir)
            await releaseEngine()
            throw deferred
        } catch {
            log(dir, "transcription failed: \(error)")
            recordFailure(error, for: dir)
            await releaseEngine()
            throw error
        }
        await releaseEngine()
    }

    /// One session from end to end: the transcript, then the banner and the
    /// hook that say it happened.
    private func transcribeAndAnnounce(_ dir: URL, override: STTChoice? = nil) async throws {
        do {
            try await transcribe(dir, override: override)
        } catch let error where engineIsCloud() && Self.looksLikeNetworkTrouble(error) {
            // No network is a wait, not a failure: the session keeps its
            // attempts and goes when the network is back. Another engine is
            // the person's choice to make, never a silent swap.
            throw TranscriptionDeferred(kind: .network, reason: "\(error)")
        }
        // After the transcript, never instead of it: transcript.json is the
        // completion marker, so anything that runs before it risks retiring a
        // session that has no transcript. Naming and summarizing both just log
        // when they can't run, and are picked up again by a later sweep.
        //
        // Outside `transcribe` rather than at the end of it because both take
        // the session's claim, and a claim held while asking for a second one
        // would refuse itself.
        await PostProcessor.finish(dir)
        notifyUser(
            title: localised("meetingcopilot — transcript ready", "meetingcopilot — расшифровка готова"),
            body: dir.lastPathComponent,
            opening: dir)
        runHook(for: dir)
    }

    private func releaseEngine() async {
        await engine?.release()
        engine = nil
        engineChoice = nil
    }

    /// A session that cannot be transcribed yet. No attempt is counted and
    /// the audio stays as it is: the next pass after the reason goes away
    /// (a choice saved, a model downloaded, the network back) does the work.
    private func recordDeferred(_ deferred: TranscriptionDeferred, for dir: URL) {
        let first = SessionState.value(dir, SessionState.Key.transcriptionDeferred) == nil
        SessionState.update(dir, with: [SessionState.Key.transcriptionDeferred: deferred.metadata])
        log(dir, "transcription waiting: \(deferred)")
        guard first else { return }
        notifyUser(
            title: localised(
                "MeetOnTrack: transcription waiting", "MeetOnTrack: расшифровка ждет"),
            body: dir.lastPathComponent + ": " + deferred.reason,
            opening: dir)
    }

    private func engineIsCloud() -> Bool {
        guard let input = engine?.input else { return false }
        switch input {
        case .perTrack: return false
        case .multichannel, .mixed: return true
        }
    }

    /// Network-shaped failures, the ones waiting fixes. A bad key or a
    /// rejected file is not one of them.
    static func looksLikeNetworkTrouble(_ error: Error) -> Bool {
        let urlErrorCodes: Set<URLError.Code> = [
            .notConnectedToInternet, .networkConnectionLost, .timedOut,
            .cannotFindHost, .cannotConnectToHost, .dnsLookupFailed,
            .internationalRoamingOff, .dataNotAllowed, .secureConnectionFailed,
        ]
        if let urlError = error as? URLError { return urlErrorCodes.contains(urlError.code) }
        return "\(error)".contains("offline") || "\(error)".contains("timed out")
    }

    /// Count a failure against the session, and retire it once retrying has
    /// stopped being reasonable, either because the error can't be fixed by
    /// repeating it, or because we've repeated it enough.
    ///
    /// A retired session keeps its audio and gets it compressed: there will
    /// never be a transcript, so holding a gigabyte an hour of PCM against a
    /// future attempt is pure waste. Delete `transcription_failed` from
    /// meta.json to offer it to the queue again.
    private func recordFailure(_ error: Error, for dir: URL) {
        let permanent = (error as? TranscriptionFailure)?.isPermanent ?? false
        let attempts =
            (SessionState.value(dir, SessionState.Key.transcriptionAttempts) as? Int ?? 0) + 1
        let gaveUp = permanent || attempts >= Self.maxAttempts
        var fields: [String: Any?] = [SessionState.Key.transcriptionAttempts: attempts]

        if gaveUp {
            fields[SessionState.Key.transcriptionFailed] = "\(error)"
            SessionState.update(dir, with: fields)
            log(dir, permanent
                ? "giving up: \(error) — retrying cannot change this"
                : "giving up after \(attempts) attempts")
            notifyUser(
                title: localised(
                    "meetingcopilot — transcription gave up", "meetingcopilot — расшифровка не вышла"),
                body: dir.lastPathComponent + localised(
                    " — audio kept, see transcribe.log",
                    " — звук сохранён, подробности в transcribe.log"),
                opening: dir
            )
            TrackCompressor.compress(sessionDir: dir)
        } else {
            SessionState.update(dir, with: fields)
            notifyUser(
                title: localised(
                    "meetingcopilot — transcription failed", "meetingcopilot — расшифровка не удалась"),
                body: dir.lastPathComponent + localised(
                    " — see transcribe.log", " — подробности в transcribe.log"),
                opening: dir
            )
        }
    }

    private static func hasGivenUp(on dir: URL) -> Bool {
        SessionState.value(dir, SessionState.Key.transcriptionFailed) != nil
    }

    private struct EmptyTranscript: TranscriptionFailure, CustomStringConvertible {
        var isPermanent: Bool { true }
        var description: String { "No speech was recognized; audio kept for a manual retry." }
    }

    private func transcribe(_ dir: URL, override: STTChoice? = nil) async throws {
        // The one place both routes into transcription meet: the app draining
        // its queue and `meetingcopilot process` given a folder by hand. Claiming here,
        // before an engine is prepared and long before anything is uploaded,
        // is what keeps two processes from paying twice for one recording.
        // Released in the `defer` so the throw and the local-engine retry give
        // the folder back as surely as the success does.
        try SessionClaim.acquire(dir, stage: .transcribe)
        defer { SessionClaim.release(dir) }

        var meta = try SessionMeta.read(from: dir)
        let (engine, choice) = try await preparedEngine(override: override)

        var audioDirectory = dir
        var cleaned: OfflineEchoAudio.Result?
        defer { cleaned?.removeAudio() }
        if Config.offlineEchoCancellation(),
           let mic = meta.track(for: "me"), let system = meta.track(for: "them") {
            let microphone = OfflineEchoAudio.Source(
                url: dir.appendingPathComponent(mic.file), channel: mic.channel ?? 0, offsetMs: mic.offsetMs)
            let reference = OfflineEchoAudio.Source(
                url: dir.appendingPathComponent(system.file), channel: system.channel ?? 0, offsetMs: system.offsetMs)
            log(dir, "removing acoustic echo from a microphone copy before transcription")
            let worker = Task.detached(priority: .utility) {
                try OfflineEchoAudio.prepare(microphone: microphone, system: reference, in: dir)
            }
            let prepared = try await withTaskCancellationHandler {
                try await worker.value
            } onCancel: { worker.cancel() }
            cleaned = prepared
            try Task.checkCancellation()
            audioDirectory = prepared.directory
            meta = SessionMeta(tracks: [
                .init(file: "mic.caf", speaker: "me", offsetMs: 0, channel: nil),
                .init(file: "system.caf", speaker: "them", offsetMs: 0, channel: nil),
            ], title: meta.title, attendees: meta.attendees, app: meta.app)
            SessionState.update(dir, with: ["audio_echo_cancellation": [
                "processor": LocalVQEAssets.processorVersion,
                "model_sha256": LocalVQEAssets.modelSHA256,
                "sample_rate": EchoCanceller.sampleRate,
                "frames": prepared.frames,
                "cache_directory": prepared.directory.lastPathComponent,
            ]])
            log(dir, "audio echo cancellation complete; original tracks kept")
        } else {
            SessionState.update(dir, with: ["audio_echo_cancellation": nil])
        }

        var merged: [Transcript.Segment]
        var echoFilterRan = false
        var echoesDropped = 0
        switch engine.input {
        case .perTrack:
            merged = try await transcribePerTrack(audioDirectory, meta: meta, engine: engine)
            merged.sort { $0.start_ms < $1.start_ms }
            // Speakers are labelled by channel: the microphone is "me", call
            // audio is "them" (owner decision 2026-10-21). Hook: a finer
            // split of the far end (a separate future task) relabels "them"
            // segments here, before the echo filter compares the two sides.
            // Only the per-track path can double-transcribe the far end: it
            // reads both tracks, and a raw mic recording through speakers has
            // their voice on it too. A diarizing engine sees the mix once, so
            // there's no duplicate for a filter to find.
            if Config.transcriptEchoFilter() {
                echoFilterRan = true
                let before = merged.count
                merged = cleaned == nil ? EchoFilter.dropEchoes(merged) : EchoFilter.dropResidualEchoes(merged)
                echoesDropped = before - merged.count
                if merged.count != before {
                    log(dir, "echo filter dropped \(before - merged.count) "
                        + "mic segment(s) duplicating system audio")
                }
            }
        case .multichannel:
            merged = try await transcribeMultichannel(audioDirectory, meta: meta, engine: engine)
            merged.sort { $0.start_ms < $1.start_ms }
            if Config.transcriptEchoFilter() {
                echoFilterRan = true
                let before = merged.count
                merged = cleaned == nil ? EchoFilter.dropEchoes(merged) : EchoFilter.dropResidualEchoes(merged)
                echoesDropped = before - merged.count
                if echoesDropped > 0 {
                    log(dir, "echo filter dropped \(echoesDropped) "
                        + "mic segment(s) duplicating system audio")
                }
            }
            merged = MultichannelSpeakerLabels.collapseSingleSides(merged)
        case .mixed:
            merged = try await transcribeMixed(audioDirectory, meta: meta, engine: engine)
            merged.sort { $0.start_ms < $1.start_ms }
        }

        guard merged.contains(where: { !$0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }) else {
            throw EmptyTranscript()
        }

        let transcript = Transcript(
            engine: engine.name,
            model: await engine.modelUsed(),
            language: choice?.language,
            created_at: ISO8601DateFormatter().string(from: Date()),
            segments: merged
        )
        try transcript.write(to: dir)
        SessionState.update(dir, with: [
            SessionState.Key.transcriptionDeferred: nil,
            "transcription_input": engine.input.metadataName,
            "echo_filter": [
                "ran": echoFilterRan,
                "dropped_segments": echoesDropped,
                "mode": cleaned == nil ? "raw_audio" : "residual_exact_phrases",
            ],
        ])
        log(dir, "done — \(merged.count) segments")

        // The audio was recorded uncompressed so it would survive a crash, and
        // that only had to hold until the transcript existed. It does now, so
        // the tracks become one stereo archive — or are deleted, if
        // `keep_audio` is off.
        //
        // Before naming and summarizing rather than after, because both of
        // those want a language model and can sit for hours waiting for one,
        // and neither reads the audio: they work from the transcript. Making
        // the gigabyte wait for a model it isn't going to be shown to would be
        // paying twice for nothing.
        TrackCompressor.settle(sessionDir: dir)
    }

    /// One pass over aligned stereo. AssemblyAI's one-based channel labels
    /// carry the side directly (`1A` is mic, `2A` is system), so this path does
    /// no envelope comparison and remains correct when the raw mic contains a
    /// quieter acoustic copy of the far end.
    private func transcribeMultichannel(
        _ dir: URL,
        meta: SessionMeta,
        engine: TranscriptionEngine
    ) async throws -> [Transcript.Segment] {
        let sharedArchive = meta.tracks.count == 2
            && meta.tracks.allSatisfy { $0.file == meta.tracks[0].file && $0.channel != nil }
        let audio = sharedArchive
            ? dir.appendingPathComponent(meta.tracks[0].file)
            : dir.appendingPathComponent(Self.multichannelFile)

        if !sharedArchive && !FileManager.default.fileExists(atPath: audio.path) {
            let temporary = dir.appendingPathComponent(Self.multichannelTemporary)
            let mic = meta.track(for: "me").map {
                TrackCompressor.StereoTrack(
                    url: dir.appendingPathComponent($0.file), offsetMs: $0.offsetMs)
            }
            let system = meta.track(for: "them").map {
                TrackCompressor.StereoTrack(
                    url: dir.appendingPathComponent($0.file), offsetMs: $0.offsetMs)
            }
            log(dir, "aligning tracks → \(Self.multichannelFile)")
            do {
                try await Task.detached(priority: .utility) {
                    _ = try TrackCompressor.encodeStereo(
                        mic: mic, system: system, to: temporary)
                    try? FileManager.default.removeItem(at: audio)
                    try FileManager.default.moveItem(at: temporary, to: audio)
                }.value
            } catch {
                try? FileManager.default.removeItem(at: temporary)
                throw error
            }
        }

        log(dir, "transcribing \(audio.lastPathComponent) (\(engine.name))")
        return MultichannelSpeakerLabels.map(try await engine.transcribe(audio))
    }

    /// One pass per track, speaker taken from the track itself.
    private func transcribePerTrack(
        _ dir: URL,
        meta: SessionMeta,
        engine: TranscriptionEngine
    ) async throws -> [Transcript.Segment] {
        var merged: [Transcript.Segment] = []
        for track in meta.tracks {
            let storedAudio = dir.appendingPathComponent(track.file)
            guard FileManager.default.fileExists(atPath: storedAudio.path) else {
                throw CocoaError(.fileReadNoSuchFile, userInfo: [NSFilePathErrorKey: storedAudio.path])
            }

            var audio = storedAudio
            var temporary: URL?
            if let channel = track.channel {
                let extracted = FileManager.default.temporaryDirectory
                    .appendingPathComponent("meetingcopilot-\(UUID().uuidString)-channel-\(channel).m4a")
                do {
                    try await Task.detached(priority: .utility) {
                        try AudioChannelExtractor.extract(
                            channel: channel, from: storedAudio, to: extracted)
                    }.value
                    audio = extracted
                    temporary = extracted
                } catch {
                    try? FileManager.default.removeItem(at: extracted)
                    log(dir, "could not extract \(track.speaker) channel in \(track.file): \(error)")
                    throw error
                }
            }

            log(dir, "transcribing \(track.file)\(track.channel.map { " channel \($0)" } ?? "") "
                + "(\(engine.name))")
            // A failed track must not turn into a successful partial transcript:
            // successful completion allows the original audio to be discarded.
            let segments: [TranscriptSegment]
            do {
                segments = try await engine.transcribe(audio)
            } catch {
                if let temporary { try? FileManager.default.removeItem(at: temporary) }
                log(dir, "could not transcribe \(track.file): \(error)")
                throw error
            }
            if let temporary { try? FileManager.default.removeItem(at: temporary) }
            let offset = TimeInterval(track.offsetMs) / 1000
            merged += segments.map {
                Transcript.Segment(
                    speaker: track.speaker,
                    start_ms: Int(($0.start + offset) * 1000),
                    end_ms: Int(($0.end + offset) * 1000),
                    text: $0.text
                )
            }
        }
        return merged
    }

    /// One pass over mixed.m4a, speaker taken from the engine's diarization
    /// and then renamed to me/them by matching each utterance back against the
    /// source tracks. The mix already carries the start offsets, so its
    /// timestamps need no shifting.
    private func transcribeMixed(
        _ dir: URL,
        meta: SessionMeta,
        engine: TranscriptionEngine
    ) async throws -> [Transcript.Segment] {
        let sharedArchive = meta.tracks.count == 2
            && meta.tracks.allSatisfy { $0.file == meta.tracks[0].file && $0.channel != nil }
        let mixed = sharedArchive
            ? dir.appendingPathComponent(meta.tracks[0].file)
            : dir.appendingPathComponent(Self.mixedFile)
        if !sharedArchive && !FileManager.default.fileExists(atPath: mixed.path) {
            log(dir, "mixing tracks → \(Self.mixedFile)")
            try await AudioMixer.mix(
                meta.tracks.map {
                    AudioMixer.Track(
                        url: dir.appendingPathComponent($0.file),
                        offset: TimeInterval($0.offsetMs) / 1000
                    )
                },
                to: mixed
            )
        }

        log(dir, "transcribing \(Self.mixedFile) (\(engine.name))")
        let segments = try await engine.transcribe(mixed)

        let names = meta.track(for: "me").flatMap { mic in
            meta.track(for: "them").flatMap { system in
                SpeakerAttribution.resolve(
                    segments: segments,
                    mic: dir.appendingPathComponent(mic.file),
                    micOffset: TimeInterval(mic.offsetMs) / 1000,
                    system: dir.appendingPathComponent(system.file),
                    systemOffset: TimeInterval(system.offsetMs) / 1000
                )
            }
        }
        if let names {
            let counts = names.reduce(into: [String: Int]()) { $0[$1, default: 0] += 1 }
            log(dir, "speakers: " + counts.sorted { $0.key < $1.key }
                .map { "\($0.key) ×\($0.value)" }
                .joined(separator: ", "))
        } else {
            log(dir, "couldn't attribute speakers to tracks — keeping diarization labels")
        }

        return segments.enumerated().map { index, segment in
            Transcript.Segment(
                speaker: names?[index] ?? segment.speaker ?? "speaker",
                start_ms: Int(segment.start * 1000),
                end_ms: Int(segment.end * 1000),
                text: segment.text
            )
        }
    }

    /// The engine for this session, from the person's speech choice (or a
    /// one-run override). Nothing here picks one: a choice that is missing or
    /// cannot run on this Mac defers the session instead.
    private func preparedEngine(
        override: STTChoice?
    ) async throws -> (TranscriptionEngine, STTChoice?) {
        if let fixedEngine {
            if engine == nil {
                try await fixedEngine.prepare()
                engine = fixedEngine
            }
            return (fixedEngine, nil)
        }
        let resolution = override.map(STTRuntime.check) ?? resolve()
        guard case .ready(let choice) = resolution else {
            throw TranscriptionDeferred(resolution)!
        }
        if let engine, engineChoice == choice { return (engine, choice) }
        await releaseEngine()
        let engine = try STTRuntime.engine(for: choice)
        try await engine.prepare()
        self.engine = engine
        engineChoice = choice
        return (engine, choice)
    }

    /// Fires the configured on_stop shell command with the session directory
    /// as its sole argument, after the transcript exists (or immediately after
    /// recording when transcription is disabled).
    private func runHook(for dir: URL) {
        guard let cmd = onStop() else { return }
        let task = Process()
        task.launchPath = "/bin/sh"
        task.arguments = ["-c", "\(cmd) \"$0\"", dir.path]
        // The session it was fired for is the only sensible place to stand.
        task.currentDirectoryURL = dir
        do {
            try task.run()
        } catch {
            log(dir, "on_stop hook failed to launch: \(error)")
        }
    }

    private func log(_ dir: URL, _ message: String) {
        appendSessionLog(message, to: dir)
    }

    private func publish(_ status: Status) {
        statusHandler?(status)
    }
}

/// The slice of meta.json the coordinator needs: which files exist, who they
/// represent, and how far each track started after the earliest one.
private struct SessionMeta {
    struct Track {
        let file: String
        let speaker: String
        let offsetMs: Int
        let channel: Int?
    }

    let tracks: [Track]
    /// What the session knows about the meeting. All of it goes into the
    /// summary prompt: knowing the subject, who was in the room and which app
    /// the call ran in measurably improves what comes back — not least because
    /// a summarizer given names can use them instead of "me" and "them".
    let title: String?
    let attendees: [String]
    let app: String?

    func track(for speaker: String) -> Track? {
        tracks.first { $0.speaker == speaker }
    }

    enum MetaError: Error, CustomStringConvertible {
        case unreadable(URL)

        var description: String {
            switch self {
            case .unreadable(let url): return "can't parse \(url.path)"
            }
        }
    }

    static func read(from dir: URL) throws -> SessionMeta {
        let url = dir.appendingPathComponent("meta.json")
        guard
            let data = try? Data(contentsOf: url),
            let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let files = json["files"] as? [String: String]
        else { throw MetaError.unreadable(url) }

        // Sessions recorded before offsets were captured default to 0 —
        // tracks start within tens of milliseconds of each other anyway.
        let offsets = json["start_offset_ms"] as? [String: Int] ?? [:]
        let channels = json["audio_channels"] as? [String: Int] ?? [:]
        var tracks: [Track] = []
        if let mic = files["mic"] {
            tracks.append(Track(
                file: mic,
                speaker: "me",
                offsetMs: offsets["mic"] ?? 0,
                channel: channels["mic"]))
        }
        if let system = files["system"] {
            tracks.append(Track(
                file: system,
                speaker: "them",
                offsetMs: offsets["system"] ?? 0,
                channel: channels["system"]))
        }
        let calendar = json["calendar"] as? [String: Any]
        return SessionMeta(
            tracks: tracks,
            title: (json["title"] as? String) ?? (calendar?["title"] as? String),
            attendees: calendar?["attendees"] as? [String] ?? [],
            app: json["app"] as? String
        )
    }
}

/// Canonical transcript. Property names are the JSON schema — this struct
/// exists to be serialized.
struct Transcript: Codable {
    struct Segment: Codable {
        let speaker: String
        let start_ms: Int
        let end_ms: Int
        let text: String
    }

    let engine: String
    let model: String
    /// The language asked for (`auto` when the model detected it).
    var language: String? = nil
    /// The speaker separation model, when one was used.
    let created_at: String
    let segments: [Segment]

    /// Render transcript.md, then write transcript.json as the completion
    /// marker. Both writes are atomic (temp file + rename), and writing the
    /// JSON last is what makes the ordering matter: resumePending treats its
    /// presence as "done", so writing it first meant a failed markdown write
    /// retired the session permanently with half its artifacts.
    func write(to dir: URL) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let json = try encoder.encode(self)

        try writeMarkdown(to: dir, names: SpeakerNames.read(from: dir))
        try json
            .write(to: dir.appendingPathComponent("transcript.json"), options: .atomic)
    }

    /// Render transcript.md against whatever names are known, which is what
    /// makes naming re-runnable: the JSON keeps the recognizer's own labels
    /// for ever, and the readable file is regenerated from it whenever a name
    /// is learned or corrected.
    func writeMarkdown(to dir: URL, names: SpeakerNames?) throws {
        try Data(rendered(title: dir.lastPathComponent, names: names).utf8)
            .write(to: dir.appendingPathComponent("transcript.md"), options: .atomic)
    }

    /// A copy with each label replaced by its known name, for readers that
    /// take the speaker straight off the segment — the summarizer, mainly,
    /// which writes "Фёдор will send the contract" only if that is what it was
    /// given to read.
    func named(with names: SpeakerNames?) -> Transcript {
        guard let names else { return self }
        return Transcript(
            engine: engine,
            model: model,
            created_at: created_at,
            segments: segments.map {
                Segment(
                    speaker: names.name(for: $0.speaker),
                    start_ms: $0.start_ms,
                    end_ms: $0.end_ms,
                    text: $0.text
                )
            }
        )
    }

    func rendered(title: String, names: SpeakerNames?) -> String {
        var lines = ["# \(title)", "", "engine: \(engine) (\(model))"]
        // A roster only earns its place when it says something the body
        // doesn't: which label a name stands for.
        let named = (names?.speakers ?? [:]).compactMap { label, entry in
            entry.name.map { "\(label) → \($0)" }
        }.sorted()
        if !named.isEmpty {
            lines.append("speakers: " + named.joined(separator: ", "))
        }
        lines.append("")
        for seg in segments {
            let who = names?.name(for: seg.speaker) ?? seg.speaker
            lines.append("**[\(Self.clock(seg.start_ms))] \(who):** \(seg.text)")
            lines.append("")
        }
        return lines.joined(separator: "\n")
    }

    private static func clock(_ ms: Int) -> String {
        let total = ms / 1000
        let h = total / 3600, m = (total % 3600) / 60, s = total % 60
        return h > 0
            ? String(format: "%d:%02d:%02d", h, m, s)
            : String(format: "%d:%02d", m, s)
    }
}
