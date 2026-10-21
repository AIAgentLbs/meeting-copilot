import AppKit
import Foundation
import Testing
@testable import meetingcopilot

@Suite(.serialized)
struct SetupTests {
    @Test("Completing setup survives a later process and reset makes it pending again")
    func completionRoundTrip() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meetingcopilot-setup-test-\(UUID().uuidString)")
        let state = root.appendingPathComponent("nested/setup.json")
        defer { try? FileManager.default.removeItem(at: root) }

        #expect(SetupState.isPending(at: state))

        SetupState.markCompleted(at: state)
        #expect(SetupState.completedVersion(at: state) == 1)
        #expect(!SetupState.isPending(at: state))

        SetupState.reset(at: state)
        #expect(SetupState.isPending(at: state))
    }

    @Test("The setup subcommand routes to the setup launcher")
    func setupCommandIsRegistered() throws {
        let command = try MeetingCopilot.parseAsRoot(["setup"])
        #expect(command is Setup)
    }

    @Test("System-audio setup retries silence and refused taps, but not a heard tone")
    @MainActor
    func systemAudioRetryPolicy() {
        #expect(SetupPermissions.needsSystemAudioTest(nil))
        #expect(SetupPermissions.needsSystemAudioTest(.silent))
        #expect(SetupPermissions.needsSystemAudioTest(.refused("permission denied")))
        #expect(!SetupPermissions.needsSystemAudioTest(.heard))
    }

    @Test("A heard tone is believed for a month, and then measured again")
    @MainActor
    func systemAudioMemory() {
        let heard = Date(timeIntervalSince1970: 1_000_000)
        let week = heard.addingTimeInterval(7 * 24 * 60 * 60)
        let quarter = heard.addingTimeInterval(90 * 24 * 60 * 60)

        #expect(SetupPermissions.rememberedSystemAudio(heardAt: heard, now: week) == .heard)
        #expect(SetupPermissions.rememberedSystemAudio(heardAt: heard, now: quarter) == nil)
        #expect(SetupPermissions.rememberedSystemAudio(heardAt: nil, now: week) == nil)
        // A clock that went backwards is not evidence of anything.
        #expect(SetupPermissions.rememberedSystemAudio(
            heardAt: quarter, now: heard) == nil)
    }

    @Test("The remembered tone survives marking setup complete, and vice versa")
    func systemAudioMemoryRoundTrip() throws {
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }
        let state = dir.appendingPathComponent("setup.json")

        let heard = Date(timeIntervalSince1970: 1_700_000_000)
        SetupState.rememberSystemAudioHeard(now: heard, at: state)
        SetupState.markCompleted(at: state)

        #expect(SetupState.systemAudioHeardAt(at: state) == heard)
        #expect(SetupState.isPending(at: state) == false)

        // `meetingcopilot setup` resets the window's own state; a measurement of the
        // machine is not part of that.
        SetupState.reset(at: state)
        #expect(SetupState.isPending(at: state))
        #expect(SetupState.systemAudioHeardAt(at: state) == heard)
    }

    @Test("Doctor reports when the system-audio path was last proven")
    func doctorReportsRememberedSystemAudioTest() {
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let check = DoctorReport.checkSystemAudio(
            isBundled: true,
            heardAt: now.addingTimeInterval(-8 * 24 * 60 * 60),
            now: now
        )

        guard case .ok = check.status else {
            Issue.record("A recent successful tone test should be reported as healthy.")
            return
        }
        #expect(check.remediation?.contains("8 days ago") == true)
    }

    @Test("A running system tap distinguishes digital zero from ordinary quiet")
    func systemAudioDigitalSilenceDecision() {
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let began = now.addingTimeInterval(-15)

        #expect(SystemAudioRecorder.isDigitallySilent(
            firstBufferAt: began, bufferCount: 100, highestPeak: 0, now: now
        ))
        #expect(!SystemAudioRecorder.isDigitallySilent(
            firstBufferAt: began, bufferCount: 100, highestPeak: 0.000_001, now: now
        ))
        #expect(!SystemAudioRecorder.isDigitallySilent(
            firstBufferAt: now.addingTimeInterval(-2), bufferCount: 100, highestPeak: 0, now: now
        ))
    }

    @Test("Far-end silence is warning-worthy for both system-audio scopes")
    func farEndSilenceCoversGlobalCapture() {
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let started = now.addingTimeInterval(-601)
        let spoke = now.addingTimeInterval(-20)

        for scope in [SystemAudioRecorder.Scope.apps(["us.zoom.xos"]), .everything] {
            #expect(RecordingSession.shouldWarnAboutFarEndSilence(
                scope: scope,
                recordingStartedAt: started,
                micLastSoundAt: spoke,
                systemLastSoundAt: nil,
                now: now
            ))
        }
    }

    @Test("First-run setup bypasses a denied microphone, not a broken recordings folder")
    func doctorRepairBoundary() {
        let microphone = Check(name: "microphone", status: .fail("denied"), remediation: nil)
        let recordings = Check(
            name: "recordings folder", status: .fail("not writable"), remediation: nil)

        #expect(DoctorReport.canContinueIntoSetup([microphone]))
        #expect(!DoctorReport.canContinueIntoSetup([microphone, recordings]))
    }

    /// A recordings root holding one session that is being recorded right now,
    /// claimed by this process — which is the only pid a test can be sure is
    /// still alive when the check runs.
    private func rootWithLiveRecording(
        named name: String, startedSecondsAgo: TimeInterval
    ) throws -> URL {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meetingcopilot-doctor-\(UUID().uuidString)", isDirectory: true)
        let session = root.appendingPathComponent(name, isDirectory: true)
        try FileManager.default.createDirectory(at: session, withIntermediateDirectories: true)
        try JSONSerialization.data(withJSONObject: [
            "pid": ProcessInfo.processInfo.processIdentifier,
            "started": ISO8601DateFormatter().string(
                from: Date().addingTimeInterval(-startedSecondsAgo)),
            "files": ["mic": "mic.caf", "system": "system.caf"],
            "trigger": "manual",
        ]).write(to: session.appendingPathComponent(".recording.json"))
        return root
    }

    @Test("Doctor says nothing about a recording when there is none")
    func quietWhenNothingIsRecording() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("meetingcopilot-doctor-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }

        if case .warn(let message) = DoctorReport.checkLiveRecording(root).status {
            Issue.record("An idle machine carries a warning nobody can act on: \(message)")
        }
    }

    @Test("Doctor names the recording in progress and how long it has run")
    func liveRecordingIsReported() throws {
        let root = try rootWithLiveRecording(named: "2026.08.20-1431 Standup",
                                             startedSecondsAgo: 252)
        defer { try? FileManager.default.removeItem(at: root) }

        let check = DoctorReport.checkLiveRecording(root)

        guard case .warn(let message) = check.status else {
            Issue.record("A live recording must be a warning, not silence.")
            return
        }
        // The folder, so it can be found, and the elapsed time, because
        // "recording" and "recording for forty minutes" are different news.
        #expect(message.contains("2026.08.20-1431 Standup"))
        #expect(message.contains("4:12"))
        #expect(check.remediation != nil)
    }

    @Test("A recording in progress never stops meetingcopilot from starting")
    func liveRecordingIsNeverAFailure() throws {
        let root = try rootWithLiveRecording(named: "2026.08.20-1431", startedSecondsAgo: 60)
        defer { try? FileManager.default.removeItem(at: root) }

        // allOK drives `throw ExitCode(1)` in `meetingcopilot doctor` and, at startup,
        // the refusal to launch. A second copy started during a meeting must
        // report the meeting and then carry on.
        #expect(DoctorReport.allOK([DoctorReport.checkLiveRecording(root)]))
    }

    /// It was the one checkbox in a window of switches, and a checkbox's
    /// title is part of the checkbox. A switch with a dead label beside it
    /// would be a smaller target than the thing it replaced, so the label
    /// still has to work.
    @Test("Keep Audio is a switch, and its label still toggles it")
    @MainActor
    func keepAudioLabelTogglesItsSwitch() throws {
        let setup = SettingsWindow()
        defer { withExtendedLifetime(setup) {} }
        let panel = try #require(NSApp.windows.last { $0.title == "\(ProductBrand.name) settings" })
        let label = try #require(panel.contentView?.allDescendants
            .compactMap { $0 as? NSTextField }
            .first { $0.stringValue == "Keep the audio after transcribing" })
        let words = try #require(label.superview as? NSStackView)
        let row = try #require(words.superview as? NSStackView)
        let toggle = try #require(row.arrangedSubviews.compactMap { $0 as? NSSwitch }.first)
        let recognizer = try #require(words.gestureRecognizers.first)

        #expect(recognizer.target === toggle)
        #expect(toggle.target != nil, "a switch nobody listens to writes nothing")

        // Unhooked first: this test is about the label reaching the switch,
        // and the action behind it writes to the config file of whoever is
        // running the suite.
        toggle.target = nil
        toggle.action = nil
        toggle.state = .off
        toggle.toggleFromItsLabel()

        #expect(toggle.state == .on)
    }

    /// A row that still had a button came out taller than its neighbours, and
    /// since everything in a row is aligned to the top the extra height
    /// landed under the text — which is how the Calendar row came to look
    /// further from System audio than the rest of the list.
    @Test("Rows carrying one line are the same height, button or no button")
    @MainActor
    func accessRowsAreOneHeight() throws {
        let rows = [
            AccessRow(title: "Microphone", detail: "Your side of the call.", action: "Allow"),
            AccessRow(title: "System audio", detail: "", action: "Allow and test"),
            AccessRow(title: "Calendar", detail: "Names the folder.", action: "Allow"),
        ]
        let box = SetupLayout.box(rows)
        // Granted, as they are on a Mac that has been through setup: the
        // first and last lose their button, the middle one keeps "Test
        // again" because macOS will not report that grant.
        rows[0].update(.granted)
        rows[1].update(.granted, note: "heard the tone", action: "Test again")
        rows[2].update(.granted)
        box.frame = NSRect(x: 0, y: 0, width: 690, height: 300)
        box.layoutSubtreeIfNeeded()

        #expect(rows[0].frame.height >= SetupLayout.rowHeight)
        #expect(rows[1].frame.height == rows[0].frame.height)
        #expect(rows[2].frame.height == rows[0].frame.height)
    }

    /// AppKit leaves the far inset out of a stack's fitting height when the
    /// stack is aligned to one edge, so a row aligned to the top came out
    /// `insets.top + content` tall and nothing else: the last line of a
    /// wrapping detail sat flush with the bottom of the row, and the tails of
    /// its p's and q's touched the hairline under it — or, in the last row of
    /// a box, the border.
    @Test("A row whose detail wraps keeps the inset under its last line")
    @MainActor
    func wrappingRowKeepsItsBottomInset() throws {
        let words = SetupLayout.detail(
            "Nvidia parakeet, 460 MB download and disk usage. Nothing leaves the "
                + "machine, and it works with no network at all.", lines: 2, width: 520)
        let row = SetupLayout.row(
            leading: NSSwitch(),
            title: SetupLayout.title("On this Mac"),
            detail: words,
            trailing: [SetupLayout.status("downloaded")])
        let box = SetupLayout.box([row])
        box.frame = NSRect(x: 0, y: 0, width: 690, height: 200)
        box.layoutSubtreeIfNeeded()

        let content = try #require(words.superview)
        let placed = row.convert(content.bounds, from: content)
        #expect(placed.height > SetupLayout.rowHeight,
                "the detail has to have wrapped, or this measures nothing")
        #expect(placed.minY == SetupLayout.rowInsets.bottom)
        #expect(row.frame.height - placed.maxY == SetupLayout.rowInsets.top)
    }

    /// The same, for the hand-built row in the Access list: **Start at login**
    /// is the one that still explains itself on a Mac that has been through
    /// none of this.
    @Test("An Access row that is still explaining itself keeps its bottom inset")
    @MainActor
    func wrappingAccessRowKeepsItsBottomInset() throws {
        let row = AccessRow(
            title: "Start at login",
            detail: "So a meeting is never missed because nobody opened meetingcopilot, and "
                + "this sentence is long enough to need a second line.",
            action: "Install")
        let box = SetupLayout.box([row])
        row.update(.notAsked)
        box.frame = NSRect(x: 0, y: 0, width: 690, height: 200)
        box.layoutSubtreeIfNeeded()

        let stack = try #require(row.subviews.first)
        let text = try #require(stack.subviews.compactMap { $0 as? NSStackView }.first)
        let placed = row.convert(text.bounds, from: text)
        #expect(placed.height > SetupLayout.rowHeight,
                "the detail has to have wrapped, or this measures nothing")
        #expect(placed.minY == SetupLayout.rowInsets.bottom)
        #expect(row.frame.height - placed.maxY == SetupLayout.rowInsets.top)
    }

    /// Which engine and model transcribe is chosen in Getting started; the
    /// form only reports it. No switch, card, key field or menu for it here.
    @Test("Setup offers no speech choice of its own and points to Getting started")
    @MainActor
    func speechIsChosenInGettingStarted() throws {
        let form = SetupForm()
        defer { form.stop() }
        form.speechResolution = { .needsChoice(STTChoice.needsChoiceMessage) }
        form.refresh()
        let views = form.view.allDescendants
        let labels = views.compactMap { ($0 as? NSTextField)?.stringValue }

        #expect(views.compactMap { $0 as? NSSecureTextField }.isEmpty)
        #expect(views.compactMap { $0 as? NSPopUpButton }.isEmpty)
        for old in ["In the cloud", "On this Mac", "Speech languages"] {
            #expect(!labels.contains(old), "\(old) is back")
        }
        #expect(labels.contains("Not chosen yet. Choose it in Getting started, in the assistant."))
        #expect(form.outstanding.contains(.speechChoice))

        form.speechResolution = {
            .ready(STTChoice(engine: STTChoice.localEngine, model: "test-model", language: "ru"))
        }
        form.refresh()
        #expect(!form.outstanding.contains(.speechChoice))
        // The engine by its name, never by the id stored in the config.
        let shown = form.view.allDescendants.compactMap { ($0 as? NSTextField)?.stringValue }
        #expect(shown.contains { $0.hasPrefix("FluidAudio · test-model.") })
        #expect(!shown.contains { $0.contains(STTChoice.localEngine) })
    }

    /// A switch nobody wired is the defect this file exists because of.
    @Test("The live transcript switch is wired, and says why it cannot run",
          .enabled(if: Platform.supportsLocalModels))
    @MainActor
    func liveSwitchIsWired() throws {
        let form = SetupForm()
        defer { form.stop() }
        let label = try #require(form.view.allDescendants
            .compactMap { $0 as? NSTextField }
            .first { $0.stringValue == "I want a live transcript during meetings" })
        let row = try #require(label.superview?.superview as? NSStackView)
        let toggle = try #require(row.arrangedSubviews.first as? NSSwitch)
        #expect(toggle.target != nil)
        #expect(toggle.action != nil)

        #expect(SetupForm.liveUnavailable(.needsChoice("nothing chosen")) == "nothing chosen")
        let cloud = STTChoice(engine: "openai", model: "test-model", language: "ru")
        #expect(SetupForm.liveUnavailable(.ready(cloud)) != nil)
    }

    @Test("The Summaries switch sits to the left of its heading")
    @MainActor
    func summariesSwitchIsFirst() throws {
        let setup = SettingsWindow()
        defer { withExtendedLifetime(setup) {} }
        let panel = try #require(NSApp.windows.last { $0.title == "\(ProductBrand.name) settings" })
        let heading = try #require(panel.contentView?.allDescendants
            .compactMap { $0 as? NSTextField }
            .first { $0.stringValue == "Summaries" })
        let header = try #require(heading.superview as? NSStackView)

        #expect(header.arrangedSubviews.first is NSSwitch)
    }

    @Test("The Summaries switch is connected to something")
    @MainActor
    func summariesSwitchIsWired() throws {
        let setup = SettingsWindow()
        defer { withExtendedLifetime(setup) {} }
        let panel = try #require(NSApp.windows.last { $0.title == "\(ProductBrand.name) settings" })
        let heading = try #require(panel.contentView?.allDescendants
            .compactMap { $0 as? NSTextField }
            .first { $0.stringValue == "Summaries" })
        let header = try #require(heading.superview as? NSStackView)
        let toggle = try #require(header.arrangedSubviews.first as? NSSwitch)

        // An NSSwitch slides under the finger whether or not anyone is
        // listening, so "it moved" is not evidence that it did anything. This
        // asks the only question that separates the two.
        #expect(toggle.target != nil)
        #expect(toggle.action != nil)
    }

    /// Both icons are in the form, and both are switches somebody listens to.
    /// The pair is worth checking together: each is only safe to offer
    /// because the other exists, and a form that grew one of them without the
    /// other would be a form that can strand a running recorder.
    @Test("Setup offers the menu bar and the Dock as two switches")
    @MainActor
    func iconSwitchesAreOffered() throws {
        let setup = SettingsWindow()
        defer { withExtendedLifetime(setup) {} }
        let panel = try #require(NSApp.windows.last { $0.title == "\(ProductBrand.name) settings" })

        for title in ["In the top menu bar on your Mac", "In the Dock"] {
            let label = try #require(
                panel.contentView?.allDescendants
                    .compactMap { $0 as? NSTextField }
                    .first { $0.stringValue == title },
                "\(title) is not in the form")
            let row = try #require(label.superview?.superview as? NSStackView)
            let toggle = try #require(row.arrangedSubviews.compactMap { $0 as? NSSwitch }.first)
            #expect(toggle.target != nil)
            #expect(toggle.action != nil)
        }
    }

    /// The sentence that is the only way back into a program with no icon.
    /// It has to appear exactly when it is true, and to say the two things
    /// that matter in the order they matter: that recording carries on, and
    /// how the window is reached.
    @Test("Giving up both icons says how to get the window back")
    func bothIconsOffExplainsItself() {
        #expect(SetupForm.noIconsNote(menuBar: true, dock: true).isEmpty)
        #expect(SetupForm.noIconsNote(menuBar: false, dock: true).isEmpty)
        #expect(SetupForm.noIconsNote(menuBar: true, dock: false).isEmpty)

        let note = SetupForm.noIconsNote(menuBar: false, dock: false)
        #expect(note.contains("keeps recording"))
        #expect(note.contains("open \(ProductBrand.name)"))
    }

    /// The AI for summaries is chosen in one place, Getting started in the
    /// assistant. The setup form keeps the on/off switch and points there.
    @Test("Setup offers no summary AI choice of its own and points to Getting started")
    @MainActor
    func summaryAIIsChosenInGettingStarted() throws {
        let setup = SettingsWindow()
        defer { withExtendedLifetime(setup) {} }
        let panel = try #require(NSApp.windows.last { $0.title == "\(ProductBrand.name) settings" })
        let views = panel.contentView?.allDescendants ?? []
        #expect(views.compactMap { $0 as? NSTextField }
            .contains { $0.stringValue.contains("Getting started") })
    }

    /// The settings window is not allowed a second, poorer copy of the setup
    /// form: two hand-written forms over one set of settings drift the moment
    /// either is edited. This is the cheapest way to notice: the speech row
    /// only exists in `SetupForm`, so finding it inside the settings window
    /// is evidence that the window shows the form rather than imitating it.
    @Test("The settings window shows the setup form itself")
    @MainActor
    func settingsReusesTheSetupForm() throws {
        let settings = SettingsWindow()
        defer { withExtendedLifetime(settings) {} }
        let panel = try #require(NSApp.windows.last { $0.title == "\(ProductBrand.name) settings" })
        let tabs = try #require(panel.contentView?.allDescendants
            .compactMap { $0 as? NSTabView }.first)

        #expect(tabs.tabViewItems.map(\.label) == ["Setup", "Advanced"])
        // Only the selected tab is in the hierarchy, and setup is the one a
        // person opening settings should land on.
        let labels = panel.contentView?.allDescendants.compactMap { ($0 as? NSTextField)?.stringValue } ?? []
        #expect(labels.contains("Speech recognition"))
    }

    @Test("Setup offers no usage statistics control")
    @MainActor
    func usageStatisticsAbsentFromSetup() throws {
        let form = SetupForm()
        defer { form.stop() }
        let title = form.view.allDescendants.compactMap { $0 as? NSTextField }
            .first { $0.stringValue == "Send usage statistics" }
        #expect(title == nil)
        #expect(!SettingsSchema.sections.flatMap(\.entries).contains { $0.path == ["analytics"] })
    }

    /// Setup is a window and also the first tab of Settings, and nothing
    /// stops both being open: the menu opens either, `meetingcopilot setup` rings the
    /// doorbell for the window, and the first run opens it by itself.
    ///
    /// Whichever one is used, the other has to agree. It did not: the file
    /// was written correctly and the window nobody had touched kept the old
    /// answer until it was closed and reopened — which reads as the change
    /// not having been saved, and is the reason to look at the file to find
    /// out what a program thinks.
    ///
    /// This is the listening half. That a write announces itself is not
    /// tested here, because `Config.update` writes to the config file of
    /// whoever is running the suite; the manual checklist covers the two
    /// halves together.
    @Test("A config change redraws every open copy of the form")
    @MainActor
    func everyOpenFormRedrawsOnAChange() throws {
        let setup = SetupForm()
        let settings = SetupForm()
        defer { setup.stop(); settings.stop() }
        let views = [setup.view, settings.view]
        // One switch, in two windows: the settings copy is on its Setup tab,
        // which is the tab a person lands on.
        let switches = try views.map { view in
            let label = try #require(view.allDescendants
                .compactMap { $0 as? NSTextField }
                .first { $0.stringValue == "Keep the audio after transcribing" })
            let row = try #require(label.superview?.superview as? NSStackView)
            return try #require(row.arrangedSubviews.compactMap { $0 as? NSSwitch }.first)
        }

        // Both are made to lie, by hand: setting the state fires no action,
        // so nothing is written and the config file is only read here.
        let stored: NSControl.StateValue = Config.keepAudio() ? .on : .off
        for toggle in switches { toggle.state = stored == .on ? .off : .on }

        NotificationCenter.default.post(name: Config.didChange, object: nil)

        for toggle in switches {
            #expect(toggle.state == stored, "An open form kept the stale answer")
        }
    }

    @Test("First run hides advanced providers and exposes a working settings action")
    @MainActor
    func firstRunIsFocused() throws {
        let form = SetupForm(firstRun: true)
        defer { form.stop() }
        let buttons = form.view.allDescendants.compactMap { $0 as? NSButton }
        let settings = try #require(buttons.first { $0.title == "Other options…" })
        var opened = false
        form.onShowSettings = { opened = true }
        _ = settings.target?.perform(settings.action, with: settings)
        #expect(opened)
        let labels = form.view.allDescendants.compactMap { ($0 as? NSTextField)?.stringValue }
        #expect(labels.contains("Speech recognition"))
        // First run downloads nothing: the speech model is chosen, and
        // fetched, in Getting started.
        #expect(!form.isDownloading)
    }

    /// The rule these windows now live by: drawing is not deciding.
    ///
    /// It is not tidiness. Every write announces itself so that each open copy
    /// of the form redraws, so a write from inside a redraw is a loop, not a
    /// wasted syscall — and short of that, the file's timestamp is the only
    /// evidence anybody has that a setting was changed. It was moving on its
    /// own: switching to the Setup tab rewrote the file byte for byte.
    ///
    /// Redrawing is what a config change causes, so posting the change is how
    /// a redraw is asked for here. The count is of the posts this test made
    /// itself; anything above that came from a redraw that wrote.
    @Test("Redrawing every open form leaves the config file alone")
    @MainActor
    func redrawingWritesNothing() throws {
        let setup = SetupWindow()
        let settings = SettingsWindow()
        defer { withExtendedLifetime((setup, settings)) {} }

        let path = Config.path
        let before = try? Data(contentsOf: path)
        let stamped = { (try? FileManager.default.attributesOfItem(atPath: path.path))?
            .first { $0.key == .modificationDate }?.value as? Date }
        let stamp = stamped()

        let posts = PostCount()
        let observer = NotificationCenter.default.addObserver(
            forName: Config.didChange, object: nil, queue: nil
        ) { _ in posts.value += 1 }
        defer { NotificationCenter.default.removeObserver(observer) }

        for _ in 0..<5 {
            NotificationCenter.default.post(name: Config.didChange, object: nil)
        }

        #expect(posts.value == 5, "a redraw wrote the config, and the write announced itself")
        #expect((try? Data(contentsOf: path)) == before, "a redraw changed the config file")
        #expect(stamped() == stamp, "a redraw rewrote the config file with the same bytes")
    }

    /// The bug itself, in the shape it actually happened in.
    ///
    /// Editing ends when a field loses focus, and a field loses focus for
    /// reasons that are nobody's decision — the tab changed, another window
    /// came forward, the window closed. Every one of those committed the row,
    /// which wrote the file back exactly as it already was: `diff` said the
    /// bytes were identical and the timestamp said somebody had just changed
    /// a setting.
    @Test("Leaving an untouched Advanced field writes nothing")
    @MainActor
    func endingEditingOnAnUntouchedRowWritesNothing() throws {
        let settings = SettingsWindow()
        defer { withExtendedLifetime(settings) {} }
        let panel = try #require(NSApp.windows.last { $0.title == "\(ProductBrand.name) settings" })

        // The Advanced tab is built with the window but only installed in the
        // hierarchy while it is the one on screen, so it is reached through
        // the tab item rather than from the content view.
        let tabs = try #require(panel.contentView?.allDescendants
            .compactMap { $0 as? NSTabView }.first)
        let advanced = try #require(tabs.tabViewItems
            .first { $0.identifier as? String == "Advanced" }?.view)
        let fields = advanced.allDescendants
            .compactMap { $0 as? NSTextField }
            .filter { $0.isEditable }
        #expect(!fields.isEmpty, "no editable rows found under Advanced")

        let path = Config.path
        let before = try? Data(contentsOf: path)
        let stamped = { (try? FileManager.default.attributesOfItem(atPath: path.path))?
            .first { $0.key == .modificationDate }?.value as? Date }
        let stamp = stamped()

        for field in fields {
            settings.controlTextDidEndEditing(
                Notification(name: NSControl.textDidEndEditingNotification, object: field))
        }

        #expect((try? Data(contentsOf: path)) == before, "leaving a field changed the config")
        #expect(stamped() == stamp, "leaving a field rewrote the config with the same bytes")
    }

    /// The wizard answers "what is left?" in one line above its buttons. The
    /// settings tab shows the same form and used to answer it only by being
    /// read row by row — so the line moved to where the form is, both times.
    @Test("The Setup tab says what is outstanding, in the wizard's own words")
    @MainActor
    func setupTabCarriesTheOutstandingLine() throws {
        let settings = SettingsWindow()
        defer { withExtendedLifetime(settings) {} }

        #expect(settings.outstandingLine == SetupForm().outstandingSentence)
        #expect(!settings.outstandingLine.isEmpty)
    }

    /// And it has to follow. A grant given in this very window, a switch
    /// thrown in the other one, a model that finished downloading — the form
    /// redraws for all of them, and a line that does not redraw with it is
    /// the same defect one level up.
    @Test("The outstanding line is redrawn whenever the form is")
    @MainActor
    func outstandingLineFollowsTheForm() throws {
        let settings = SettingsWindow()
        defer { withExtendedLifetime(settings) {} }
        let panel = try #require(NSApp.windows.last { $0.title == "\(ProductBrand.name) settings" })

        let truth = settings.outstandingLine
        let label = try #require(panel.contentView?.allDescendants
            .compactMap { $0 as? NSTextField }
            .first { $0.stringValue == truth })
        label.stringValue = "something that is not true"

        NotificationCenter.default.post(name: Config.didChange, object: nil)

        #expect(settings.outstandingLine == truth)
    }

    /// Both halves of the sentence matter. Somebody opens that tab to be
    /// reassured at least as often as to repair something, and a line that
    /// only appears when something is wrong leaves them counting green ticks.
    @Test("The sentence says the good news as well as the bad")
    func outstandingSentenceShapes() {
        #expect(SetupForm.sentence(for: []) == "Everything \(ProductBrand.name) needs is granted.")
        #expect(SetupForm.sentence(for: [.microphone]) == "One thing left: microphone")
        #expect(SetupForm.sentence(for: [.microphone, .systemAudio])
            == "Left: microphone, system audio")
    }

    @Test("Summary key probes use each provider's authenticated models endpoint")
    func summaryKeyProbeRequests() {
        let anthropic = SummaryKeyProbe.request(provider: .anthropic, key: "anthropic-secret")
        #expect(anthropic.url?.absoluteString == "https://api.anthropic.com/v1/models?limit=1")
        #expect(anthropic.httpMethod == "GET")
        #expect(anthropic.value(forHTTPHeaderField: "x-api-key") == "anthropic-secret")
        #expect(anthropic.value(forHTTPHeaderField: "anthropic-version") == "2023-06-01")

        let openAI = SummaryKeyProbe.request(provider: .openAI, key: "openai-secret")
        #expect(openAI.url?.absoluteString == "https://api.openai.com/v1/models")
        #expect(openAI.httpMethod == "GET")
        #expect(openAI.value(forHTTPHeaderField: "authorization") == "Bearer openai-secret")
    }

    @Test("A box and its hairlines are re-read when the Mac changes appearance")
    @MainActor
    func boxBorderFollowsAppearance() throws {
        let box = SetupLayout.box([SetupLayout.title("First"), SetupLayout.title("Second")])
        let hairline = try #require(box.subviews.compactMap { $0 as? Hairline }.first)

        box.appearance = NSAppearance(named: .darkAqua)
        #expect(box.layer?.borderColor == separator(in: .darkAqua))
        #expect(hairline.layer?.backgroundColor == separator(in: .darkAqua))

        box.appearance = NSAppearance(named: .aqua)
        #expect(box.layer?.borderColor == separator(in: .aqua))
        #expect(hairline.layer?.backgroundColor == separator(in: .aqua))
    }

    /// What `separatorColor` comes to under a named appearance — the value a
    /// correctly tinted layer should be holding.
    @MainActor
    private func separator(_ alpha: CGFloat? = nil, in name: NSAppearance.Name) -> CGColor? {
        var resolved: CGColor?
        NSAppearance(named: name)?.performAsCurrentDrawingAppearance {
            let colour = NSColor.separatorColor
            resolved = (alpha.map(colour.withAlphaComponent) ?? colour).cgColor
        }
        return resolved
    }

    @Test("The summary switch alone decides whether summaries are written")
    func summarySwitchDecides() {
        var settings = Config.SummarySettings()
        #expect(settings.writesSummaries)
        settings.enabled = false
        #expect(!settings.writesSummaries)
    }
}

private extension NSView {
    var allDescendants: [NSView] {
        subviews + subviews.flatMap(\.allDescendants)
    }
}

/// A counter the notification centre can reach from inside its closure. Posts
/// are delivered synchronously on the thread that made them, so there is no
/// race here to protect against — the box is for the compiler.
private final class PostCount: @unchecked Sendable {
    var value = 0
}
