import AppKit
import Foundation

/// Everything a new installation is asked: the permissions macOS will
/// otherwise demand at the worst possible moment, and the choices meetingcopilot can't
/// sensibly make for you — what writes the transcript, what writes the
/// summary, where the files go, and whether it all runs by itself.
///
/// It is a form rather than a window because it is shown in two places. The
/// setup window wraps it in a wizard — a footer that names what is left and a
/// button that does the next thing — and the settings window shows the same
/// form as its first tab. One form, so the two can never drift into
/// disagreeing about what meetingcopilot offers; and there is nothing in setup a
/// person should have to reopen setup to change.
///
/// It is AppKit rather than a terminal wizard for a reason that isn't
/// cosmetic. macOS grants microphone and system-audio capture to the process
/// that asks; a wizard run from a shell teaches the system that Terminal may
/// record, and the daemon then captures a full-length silent file with nothing
/// to show for it (.issues/rca-002). The asking has to happen here, inside the
/// program that will do the recording.
///
/// Everything it shows is read from the machine rather than assumed: whether a
/// grant exists, and whether the speech recognition chosen in Getting started
/// can run. Nothing here says "should work", and nothing here downloads.
@MainActor
final class SetupForm: NSObject {
    let firstRun: Bool
    var onShowSettings: (() -> Void)?
    /// Whether a recording is in progress. Registering at login and testing
    /// system audio both disturb a running recording, and nothing in this
    /// form is worth losing a meeting for.
    var isRecording: (() -> Bool)?
    /// Called whenever anything a host displays *about* the form may have
    /// changed — what is still outstanding, what the next action is. The
    /// setup window's footer is written from it, and the settings window
    /// redraws its other tab.
    var onStateChange: (() -> Void)?

    /// What the speech recognition choice in Getting started adds up to. A
    /// seam so a test can say "nothing chosen" without a config file. Read
    /// only: the migration of old settings belongs to the code that runs
    /// sessions, not to a window redrawing itself.
    var speechResolution: @MainActor () -> STTResolution = {
        STTRuntime.resolve(stored: STTChoice.stored(in: Config.current()))
    }

    /// The form itself, for a host to put in a scroll view.
    let view = FlippedStackView()

    /// Redraws this copy when anything writes the config file — the other
    /// window showing the same form, the Advanced tab beside it, or the
    /// status window's live-transcript switch.
    private var configWatch: ConfigWatch.Token?


    private let launchRow = AccessRow(
        title: localised("Start at login", "Запуск при входе"),
        detail: localised(
            "So a meeting is never missed because nobody opened MeetOnTrack.",
            "Чтобы встреча не пропала из-за того, что MeetOnTrack никто не открыл."),
        action: localised("Install", "Включить"),
        grantedNote: localised("installed", "включено"))
    private let micRow = AccessRow(
        title: localised("Microphone", "Микрофон"),
        detail: localised("Your side of the call.", "Ваша сторона разговора."),
        action: localised("Allow", "Разрешить"),
        grantedNote: localised("allowed", "разрешено"))
    private let audioRow = AccessRow(
        title: localised("System audio", "Звук системы"),
        detail: "",
        action: localised("Allow and test", "Разрешить и проверить"),
        grantedNote: localised("heard the tone", "тон услышан"))
    private let calendarRow = AccessRow(
        title: localised("Google Calendar", "Google Календарь"),
        detail: localised(
            "Uses the Google account connected to this Mac; iCloud is excluded.",
            "Использует Google-аккаунт на этом Mac; iCloud исключён."),
        action: localised("Allow", "Разрешить"),
        grantedNote: localised("allowed", "разрешено"),
        optional: true)

    private let speechStatus = SetupLayout.detail("", lines: 3, width: 440)
    private let keepAudio = NSSwitch()
    private let liveTranscription = NSSwitch()
    private let liveDetail = SetupLayout.detail("", lines: 4, width: 520)

    private let summariesOn = NSSwitch()
    private let recordingsPath = NSTextField(labelWithString: "")
    private let menuBarIcon = NSSwitch()
    private let dockIcon = NSSwitch()
    /// Says what is left when both icons are off. Present only then: it is a
    /// consequence, not a warning, and a line explaining how to get back to a
    /// window you are looking at is noise until it is the only way.
    private let noIconsNote: NSTextField = {
        let label = SetupLayout.status()
        label.lineBreakMode = .byWordWrapping
        // Three, though two is enough in both languages at the width the
        // setup window opens at: the settings window is narrower, and a
        // sentence that is the only way back into the program is the last one
        // that should end in an ellipsis.
        label.maximumNumberOfLines = 3
        label.preferredMaxLayoutWidth = 520
        return label
    }()
    private let autoRecord = NSSwitch()

    init(firstRun: Bool = false) {
        self.firstRun = firstRun
        super.init()

        let form = view
        form.orientation = .vertical
        form.alignment = .leading
        form.spacing = SetupLayout.sectionGap
        form.edgeInsets = NSEdgeInsets(
            top: 22, left: SetupLayout.gutter, bottom: 22, right: SetupLayout.gutter)

        if firstRun {
            let welcome = SetupLayout.detail(localised(
                "Record both sides of a call, read the live transcript and ask questions with your project context. Start here; optional services stay in Settings.",
                "Записывайте обе стороны звонка, читайте стенограмму и задавайте вопросы с учетом своего проекта. Здесь только первый запуск; дополнительные сервисы доступны в настройках."), lines: 4, width: 580)
            form.addArrangedSubview(welcome)
        }
        form.addArrangedSubview(SetupLayout.section(
            localised("Access", "Доступ"),
            content: SetupLayout.box(firstRun ? [launchRow, micRow, audioRow] : [launchRow, micRow, audioRow, calendarRow])))

        if firstRun {
            form.addArrangedSubview(SetupLayout.section(
                localised("Speech recognition", "Распознавание речи"),
                content: SetupLayout.box([speechRow()])))
            form.addArrangedSubview(SetupLayout.detail(localised(
                "Speech recognition and the AI for answers are chosen in Getting started, in the assistant.",
                "Распознавание речи и ИИ для ответов выбираются в разделе «Начать работу» в помощнике."), lines: 3, width: 580))
            let settings = SetupLayout.actionButton(localised("Other options…", "Другие настройки…"), target: self, action: #selector(showOtherSettings))
            form.addArrangedSubview(settings)
        } else {
        var transcription: [NSView] = [SetupLayout.box([speechRow()])]
        // The live transcript is a local streaming model, so on an Intel Mac
        // there is nothing behind the switch. Left out rather than shown
        // switched off: an offer that can never be accepted.
        if Platform.supportsLocalModels {
            transcription.append(SetupLayout.box([liveTranscriptionRow()]))
        }
        form.addArrangedSubview(SetupLayout.section(
            localised("Transcription", "Расшифровка"),
            content: SetupLayout.group(transcription)))

        form.addArrangedSubview(SetupLayout.section(
            localised("Files", "Файлы"),
            content: SetupLayout.box([folderRow(), keepAudioRow()])))

        form.addArrangedSubview(SetupLayout.section(
            localised("Summaries", "Саммари"),
            leading: summariesOn,
            content: summaryChoices()))

        form.addArrangedSubview(SetupLayout.section(
            localised("Where MeetOnTrack shows up", "Где видно MeetOnTrack"),
            content: SetupLayout.group(
                [SetupLayout.box([menuBarIconRow(), dockIconRow()]), noIconsNote],
                spacing: SetupLayout.headerGap)))

        // No heading of its own: one switch is not a section, and it belongs
        // at the end because it is the thing that makes all of the above run
        // without anyone opening this form again.
        form.addArrangedSubview(SetupLayout.box([autoRecordRow()]))
        }

        for view in form.arrangedSubviews {
            view.widthAnchor.constraint(
                equalTo: form.widthAnchor, constant: -2 * SetupLayout.gutter).isActive = true
        }

        wireActions()
        refresh()
        configWatch = ConfigWatch.observe { [weak self] in self?.refresh() }
    }

    @objc private func showOtherSettings() { onShowSettings?() }

    /// Re-read the machine and the config file. A host calls this when the
    /// form comes back on screen: the menu and the status window both write
    /// `auto_record.enabled`, and a form showing yesterday's answer is worse
    /// than no form at all.
    func reload() {
        refresh()
    }

    /// The setup window calls this on the way out. Nothing in the form
    /// outlives it any more: it never downloads.
    func stop() {}
    // MARK: - building

    /// Which engine and model transcribe is chosen in one place, Getting
    /// started in the assistant (`stt.choice` in the shared config). This row
    /// only says what that choice adds up to on this Mac.
    private func speechRow() -> NSView {
        SetupLayout.row(
            symbol: "text.bubble",
            title: SetupLayout.title(localised("Speech recognition", "Распознавание речи")),
            detail: speechStatus)
    }

    private func liveTranscriptionRow() -> NSView {
        liveTranscription.target = self
        liveTranscription.action = #selector(liveTranscriptionToggled)
        return SetupLayout.row(
            leading: liveTranscription,
            title: SetupLayout.title(localised(
                "I want a live transcript during meetings",
                "Показывать расшифровку прямо во время встречи")),
            detail: liveDetail)
    }

    /// Where the recordings live, and the one thing worth saying about the
    /// default: it is outside Documents, Desktop and Downloads, so macOS never
    /// has to ask a background recorder for permission to write there.
    private func folderRow() -> NSView {
        recordingsPath.font = SetupLayout.monoFont
        recordingsPath.lineBreakMode = .byTruncatingMiddle

        return SetupLayout.row(
            symbol: "folder",
            title: recordingsPath,
            detail: SetupLayout.detail(
                localised(
                    "Outside Documents and Desktop, so macOS never has to ask.",
                    "Вне Документов и Рабочего стола — macOS не будет спрашивать."),
                lines: 1),
            trailing: [SetupLayout.actionButton(
                localised("Choose…", "Выбрать…"),
                target: self, action: #selector(chooseFolder))])
    }

    @objc private func chooseFolder() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.canCreateDirectories = true
        panel.allowsMultipleSelection = false
        panel.directoryURL = Config.resolveRoot(cliOverride: nil)
        panel.prompt = localised("Use folder", "Выбрать папку")
        guard panel.runModal() == .OK, let chosen = panel.url else { return }

        // Store it the way a person would write it: a path under the home
        // directory stays readable, and stays right if the account is renamed.
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let path = chosen.path.hasPrefix(home)
            ? "~" + chosen.path.dropFirst(home.count)
            : chosen.path
        Config.update(path: ["recordings_dir"], value: String(path))
        refresh()
    }

    /// The one checkbox in a window of switches, and the only row whose words
    /// did not start where the words above them started — the checkbox stood
    /// in the column the folder symbol uses, and its title six points to the
    /// left of the path's. It is a switch now, and its label still toggles it.
    private func keepAudioRow() -> NSView {
        keepAudio.target = self
        keepAudio.action = #selector(keepAudioChanged)
        return SetupLayout.row(
            symbol: "waveform",
            title: SetupLayout.title(localised(
                "Keep the audio after transcribing", "Оставлять звук после расшифровки")),
            trailing: [keepAudio])
    }

    /// Which AI writes summaries and names speakers is chosen in one place,
    /// Getting started in the assistant (`ai.choice` in the shared config);
    /// this section only switches summaries on and off.
    private func summaryChoices() -> NSView {
        // Without this the switch still slides when you push it while nothing
        // is written, and every meeting is summarised anyway.
        summariesOn.target = self
        summariesOn.action = #selector(summariesToggled)
        return SetupLayout.detail(
            localised(
                "Choose the AI for summaries and speaker names in Getting started, in the assistant. The chosen AI receives the transcript, meeting title and calendar participants.",
                "ИИ для саммари и имен говорящих выбирается в разделе «Начать работу» в помощнике. Выбранный ИИ получает расшифровку, название встречи и участников из календаря."),
            lines: 3,
            width: 520)
    }

    /// The two places a person can find a running meetingcopilot, each of which can be
    /// given up. Both, if they like: what is left then is the program itself,
    /// which is opened the way any program is opened, and `noIconsNote` says
    /// so at the moment it becomes true.
    private func menuBarIconRow() -> NSView {
        menuBarIcon.target = self
        menuBarIcon.action = #selector(iconsChanged)
        return SetupLayout.row(
            leading: menuBarIcon,
            title: SetupLayout.title(localised("In the top menu bar on your Mac", "В верхнем меню Mac")),
            detail: SetupLayout.detail(
                localised(
                    "The MeetOnTrack M icon shows the recording timer. Click it to open the assistant or recording controls.",
                    "Значок M MeetOnTrack показывает время записи. Нажмите, чтобы открыть помощник или управление записью."),
                lines: 2, width: 520))
    }

    private func dockIconRow() -> NSView {
        dockIcon.target = self
        dockIcon.action = #selector(iconsChanged)
        return SetupLayout.row(
            leading: dockIcon,
            title: SetupLayout.title(localised("In the Dock", "В доке")),
            detail: SetupLayout.detail(
                localised(
                    "And in ⌘-Tab. The Dock cannot run out of room the way the menu bar can, "
                        + "and clicking the icon shows the window.",
                    "И в ⌘-Tab. В доке, в отличие от строки меню, место не кончается, "
                        + "а по щелчку значка открывается окно."),
                lines: 2, width: 520))
    }

    private func autoRecordRow() -> NSView {
        autoRecord.target = self
        autoRecord.action = #selector(autoRecordToggled)
        return SetupLayout.row(
            leading: autoRecord,
            title: SetupLayout.title(localised(
                "Start recording automatically when a call app takes the mic",
                "Начинать запись, когда приложение звонка берёт микрофон")),
            detail: SetupLayout.detail(
                localised(
                    "And stop when it lets go. A call shorter than 45 seconds is thrown away.",
                    "И заканчивать, когда отпустит. Звонок короче 45 секунд выбрасывается."),
                lines: 2, width: 520))
    }


    /// What is left when neither icon is on, and nothing at all while either
    /// is. Static and free of AppKit so the sentence can be checked without a
    /// window: it is the only instruction meetingcopilot gives for reaching itself,
    /// and it is shown exactly when it is the only way in.
    nonisolated static func noIconsNote(menuBar: Bool, dock: Bool) -> String {
        guard !menuBar, !dock else { return "" }
        return localised(
            "MeetOnTrack keeps recording with no icon anywhere. To bring the window back, open MeetOnTrack "
                + "again — from Spotlight, or from Applications.",
            "MeetOnTrack продолжит записывать, но его нигде не будет видно. Чтобы вернуть окно, "
                + "откройте MeetOnTrack ещё раз — из Spotlight или из папки «Программы».")
    }

    /// "18 Aug" — enough to tell this week from last spring, and short enough
    /// to sit beside a row title.
    ///
    /// Built on each use rather than once. A `static let` is made the first
    /// time anything asks for it and keeps whatever language was in force
    /// then — which is right in a program that settles its language at
    /// startup and wrong the moment anything else changes it, and a formatter
    /// that is right by luck is worth less than one that is right by
    /// construction. Two rows a person opens a window to read is not a rate
    /// worth caching for.
    private static var day: DateFormatter {
        let formatter = DateFormatter()
        // The window's language, on the Mac's own region: a Russian window
        // saying "heard the tone · 19 Aug" is two languages in one line, and
        // a locale built from the language alone would take the day and month
        // out of the order this Mac writes them in as well.
        var locale = Locale.Components(locale: .current)
        locale.languageComponents.languageCode = .init(InterfaceLanguage.current.rawValue)
        formatter.locale = Locale(components: locale)
        formatter.setLocalizedDateFormatFromTemplate("d MMM")
        return formatter
    }

    // MARK: - actions

    private func wireActions() {
        launchRow.onAct = { [weak self] in self?.startAtLogin() }
        micRow.onAct = { [weak self] in Task { await self?.askMicrophone() } }
        audioRow.onAct = { [weak self] in Task { await self?.testSystemAudio() } }
        calendarRow.onAct = { [weak self] in Task { await self?.askCalendar() } }
    }

    /// Written the moment they are clicked, and taken up the moment they are
    /// written — the app reads the same file change and moves its icons. So
    /// the switch that has just emptied the menu bar is on screen beside the
    /// evidence of it, which is what makes turning both off a safe thing to
    /// let anyone do.
    ///
    /// One action for both switches, because `Config.update` writes only what
    /// differs: the half nobody touched costs a comparison and leaves the
    /// file, and its timestamp, alone.
    @objc private func iconsChanged() {
        Config.update(path: ["menu_bar_icon"], value: menuBarIcon.state == .on ? nil : false)
        Config.update(path: ["dock_icon"], value: dockIcon.state == .on ? nil : false)
    }

    @objc private func keepAudioChanged() {
        Config.update(path: ["keep_audio"], value: keepAudio.state == .on ? true : nil)
    }

    @objc private func liveTranscriptionToggled() {
        Config.update(
            path: ["live_transcription", "enabled"], value: liveTranscription.state == .on ? true : nil)
        refresh()
    }

    @objc private func autoRecordToggled() {
        Config.update(
            path: ["auto_record", "enabled"], value: autoRecord.state == .on ? nil : false)
    }


    @objc private func summariesToggled() {
        Config.update(path: ["summary", "enabled"], value: summariesOn.state == .on ? nil : false)
        refresh()
    }

    /// Register with Login Items, the way every other application does.
    private func startAtLogin() {
        if isRecording?() == true {
            report(launchRow, localised(
                "not while a recording is running — stop it and try again",
                "не сейчас: идёт запись — остановите её и попробуйте снова"))
            return
        }
        do {
            let state = try LoginItem.register()
            // Registered but held: macOS wants a person to say yes, and the
            // only place they can is System Settings.
            if state == .needsApproval { LoginItem.openSettings() }
        } catch {
            report(launchRow, localised("couldn't register at login: ", "не удалось включить: ")
                + error.localizedDescription)
        }
        refresh()
    }

    private func askMicrophone() async {
        let state = await SetupPermissions.requestMicrophone()
        if state == .denied { SetupPermissions.openSettings(.microphone) }
        refresh()
    }

    private func askCalendar() async {
        let state = await SetupPermissions.requestCalendar()
        calendarGrant = state
        if state == .denied { SetupPermissions.openSettings(.calendar) }
        refresh()
    }

    /// What the calendar prompt answered, for as long as this window is open.
    /// Kept because EventKit will not admit to a grant given in this process
    /// until the next launch, and a row that still says "optional" after the
    /// person has just said yes is the button looking broken all over again.
    private var calendarGrant: SetupPermissions.State?

    private func testSystemAudio() async {
        audioRow.working(localised("playing a tone…", "играет тон…"))
        let result = await SetupPermissions.testSystemAudio()
        systemAudio = result
        if result == .heard { SetupState.rememberSystemAudioHeard() }
        switch result {
        case .heard:
            break
        case .silent, .refused:
            SetupPermissions.openSettings(.systemAudio)
        }
        refresh()
    }

    /// Seeded from the last tone that was heard, because macOS will not tell
    /// us and a working Mac should not be asked to prove itself every time.
    private lazy var systemAudio: SetupPermissions.SystemAudioResult? =
        SetupPermissions.rememberedSystemAudio(heardAt: SetupState.systemAudioHeardAt())

    // MARK: - reading the machine

    /// Summaries are on and no runnable AI is chosen for them in Getting
    /// started: the one line somebody reads before pressing Done says so.
    private var chosenSummaryIsMissing: Bool {
        guard Config.summary().enabled else { return false }
        if case .ready = AIChoice.resolve(in: Config.current()) { return false }
        return true
    }

    // MARK: - refresh

    /// Redraw everything from the machine and the config file. Cheap: no
    /// subprocesses, no network — those write into fields this only reads.
    /// Public because the settings window's other tab writes the same keys,
    /// and a change made there has to reach these controls rather than wait
    /// for the window to be reopened.
    func refresh() {
        switch LoginItem.status() {
        case .enabled:
            launchRow.update(.granted, note: localised("on", "включено"))
        case .needsApproval:
            launchRow.update(
                .denied,
                detail: localised(
                    "macOS wants this allowed in Login Items.",
                    "macOS хочет, чтобы это разрешили в объектах входа."),
                action: localised("Open Settings", "Открыть настройки"))
        case .notRegistered:
            launchRow.update(.notAsked, detail: localised(
                "So a meeting is never missed.", "Чтобы ни одна встреча не пропала."))
        case .unavailable:
            launchRow.update(
                .notAsked,
                detail: localised(
                    "Only MeetOnTrack.app can register itself; this is a bare build.",
                    "Зарегистрировать себя может только MeetOnTrack.app, а это голая сборка."))
        }
        micRow.update(SetupPermissions.microphone())
        calendarRow.update(calendarGrant ?? SetupPermissions.calendar())

        switch systemAudio {
        case .heard:
            audioRow.update(
                .granted,
                note: SetupState.systemAudioHeardAt().map {
                    localised("heard the tone · ", "тон услышан · ")
                        + Self.day.string(from: $0)
                } ?? localised("heard the tone", "тон услышан"),
                action: localised("Test again", "Проверить ещё раз"))
        case .silent:
            audioRow.update(.denied, detail: localised(
                "Recorded silence. Check the grant, or turn the volume up, and test again.",
                "Записалась тишина. Проверьте разрешение или прибавьте громкость и "
                    + "попробуйте снова."))
        case .refused(let why): audioRow.update(.denied, detail: why)
        case nil: audioRow.update(.notAsked)
        }

        let config = Config.raw()
        let speech = speechResolution()
        refreshSpeech(speech)
        keepAudio.state = Config.keepAudio() ? .on : .off
        liveTranscription.state = Config.liveTranscriptionEnabled() ? .on : .off
        refreshLive(speech)

        let root = Config.resolveRoot(cliOverride: nil).path
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        recordingsPath.stringValue = root.hasPrefix(home)
            ? "~" + root.dropFirst(home.count)
            : root

        let summary = Config.summary()
        summariesOn.state = summary.enabled ? .on : .off

        menuBarIcon.state = Config.menuBarIcon() ? .on : .off
        dockIcon.state = Config.dockIcon() ? .on : .off
        noIconsNote.stringValue = Self.noIconsNote(
            menuBar: Config.menuBarIcon(), dock: Config.dockIcon())
        noIconsNote.isHidden = noIconsNote.stringValue.isEmpty

        let autoRecordOn = (config["auto_record"] as? [String: Any])?["enabled"] as? Bool ?? true
        autoRecord.state = autoRecordOn ? .on : .off

        highlightNextGrant()
        onStateChange?()
    }

    /// The speech row, in the form's language around the engine's own words:
    /// the engine's name and the model's label as discovery lists them.
    private func refreshSpeech(_ resolution: STTResolution) {
        switch resolution {
        case .ready(let choice):
            speechStatus.stringValue = "\(STTCatalog.engineName(choice.engine)) · \(choice.model). " + localised(
                "Change it in Getting started, in the assistant.",
                "Изменить можно в разделе «Начать работу» в помощнике.")
            speechStatus.textColor = .secondaryLabelColor
        case .needsChoice:
            speechStatus.stringValue = localised(
                "Not chosen yet. Choose it in Getting started, in the assistant.",
                "Пока не выбрано. Выберите в разделе «Начать работу» в помощнике.")
            speechStatus.textColor = .systemOrange
        case .unavailable(let reason):
            speechStatus.stringValue = localised("Can't run yet: ", "Пока не может работать: ") + reason
            speechStatus.textColor = .systemOrange
        }
    }

    /// The live row says why it cannot run, never offers a download.
    private func refreshLive(_ resolution: STTResolution) {
        var text = localised(
            "Uses the speech model chosen in Getting started. Nothing leaves this Mac.",
            "Использует модель распознавания, выбранную в «Начале работы». С мака ничего не уходит.")
        if Config.liveTranscriptionEnabled(), let reason = Self.liveUnavailable(resolution) {
            text += "\n" + localised("Not available: ", "Недоступно: ") + reason
        }
        liveDetail.stringValue = text
    }

    /// Why the live transcript cannot run with this choice, or nil when it can.
    nonisolated static func liveUnavailable(_ resolution: STTResolution) -> String? {
        guard case .ready(let choice) = resolution else { return resolution.reason }
        return LiveModels.unavailableReason(choice)
    }

    /// Tint the row the primary button is about to act on — and only that
    /// one. The order below is the same one `nextAction` walks, because the
    /// highlight is meant to point at the button, not compete with it.
    private func highlightNextGrant() {
        let rows = [launchRow, micRow, audioRow, calendarRow]
        let pending: AccessRow?
        if SetupPermissions.needsStartAtLogin {
            pending = launchRow
        } else if SetupPermissions.microphone() != .granted {
            pending = micRow
        } else if SetupPermissions.needsSystemAudioTest(systemAudio) || systemAudio == .silent {
            pending = audioRow
        } else {
            pending = nil
        }
        for row in rows { row.setAttention(row === pending) }
    }

    /// What the setup window's primary button will do, or nil when there is
    /// nothing left to offer. The order is the order things must happen in:
    /// the agent first, because a grant given to the wrong process is worse
    /// than none.
    var nextAction: (() -> Void)? {
        if SetupPermissions.needsStartAtLogin {
            return { [weak self] in self?.startAtLogin() }
        }
        if SetupPermissions.microphone() != .granted {
            return { [weak self] in Task { await self?.askMicrophone() } }
        }
        if SetupPermissions.needsSystemAudioTest(systemAudio) {
            return { [weak self] in Task { await self?.testSystemAudio() } }
        }
        return nil
    }


    /// What the machine still owes, in the order it has to be dealt with.
    /// The setup window's footer is this list in a sentence and its button is
    /// `nextAction`; all three are here so they cannot disagree.
    var outstanding: [Missing] {
        var left: [Missing] = []
        if SetupPermissions.needsStartAtLogin { left.append(.startAtLogin) }
        if SetupPermissions.microphone() != .granted { left.append(.microphone) }
        if systemAudio != .heard { left.append(.systemAudio) }
        if case .needsChoice = speechResolution() { left.append(.speechChoice) }
        // Summaries on with nothing chosen to write them is not "everything
        // granted".
        if !firstRun, chosenSummaryIsMissing { left.append(.summaryTool) }
        return left
    }

    /// One thing the machine still owes.
    ///
    /// A case rather than the words for it, because the words are read by a
    /// person and the case is read by the program: the footer button asks
    /// whether parakeet is on this list, and it asked by comparing against the
    /// string the window was showing. That worked while there was one language
    /// to show it in.
    enum Missing: Sendable, Equatable {
        case startAtLogin
        case microphone
        case systemAudio
        /// No speech recognition is chosen in Getting started.
        case speechChoice
        /// Summaries are on, and no AI is chosen for them in Getting started.
        case summaryTool

        var described: String {
            switch self {
            case .startAtLogin: return localised("start at login", "запуск при входе")
            case .microphone: return localised("microphone", "микрофон")
            case .systemAudio: return localised("system audio", "звук системы")
            case .speechChoice:
                return localised("choose speech recognition in Getting started",
                                 "выбрать распознавание речи в разделе «Начать работу»")
            case .summaryTool:
                return localised("choose AI for summaries in Getting started",
                                 "выбрать ИИ для саммари в разделе «Начать работу»")
            }
        }
    }

    /// The same list in a sentence, for whatever is showing it.
    ///
    /// Both windows say this, so both say it the same way: the setup window
    /// in its footer, the settings window under the Setup tab. It says the
    /// good news as well as the bad, because most of the time somebody opens
    /// that tab to be reassured rather than to repair anything, and a line
    /// that only ever appears when something is wrong leaves them counting
    /// green ticks to find out whether it is.
    var outstandingSentence: String { Self.sentence(for: outstanding) }

    /// Separate from the machine, and `nonisolated` to say so: it reads no
    /// permission and no file, which is what lets the three shapes of it be
    /// tested without granting or revoking anything.
    nonisolated static func sentence(for outstanding: [Missing]) -> String {
        let named = outstanding.map(\.described)
        switch named.count {
        case 0:
            return localised(
                "Everything MeetOnTrack needs is granted.",
                "Всё, что нужно MeetOnTrack, разрешено.")
        case 1:
            return localised("One thing left: ", "Осталось одно: ") + named[0]
        default:
            return localised("Left: ", "Осталось: ") + named.joined(separator: ", ")
        }
    }

    /// Whether a model is coming down right now. Never, from this form; kept
    /// for the setup window, which asks.
    var isDownloading: Bool { false }

    /// What the setup window's primary button says, given where things stand.
    var nextActionTitle: String {
        if SetupPermissions.needsStartAtLogin {
            return LoginItem.status() == .needsApproval
                ? localised("Open Login Items", "Открыть объекты входа")
                : localised("Start at login", "Запускать при входе")
        }
        if SetupPermissions.microphone() != .granted {
            return localised("Allow microphone", "Разрешить микрофон")
        }
        if SetupPermissions.needsSystemAudioTest(systemAudio) {
            return localised("Allow and test", "Разрешить и проверить")
        }
        if firstRun { return localised("Open MeetOnTrack", "Открыть MeetOnTrack") }
        return localised("Done", "Готово")
    }
    private func report(_ row: AccessRow, _ message: String) {
        row.update(.denied, detail: message)
    }
}

// MARK: - one permission

/// A row in the Access list: where it stands, what it's for, and the one
/// button that changes it.
@MainActor
final class AccessRow: NSView, LayerTinted {
    var onAct: (() -> Void)?

    /// Whether this is the row being asked for right now; see `setAttention`.
    private var wantsAttention = false

    private let mark = NSImageView()
    private let title: NSTextField
    private let note = NSTextField(labelWithString: "")
    private let detail: NSTextField
    private let button: NSButton
    private let stack: NSStackView
    private let defaultDetail: String
    private let defaultAction: String
    private let grantedNote: String
    private let isOptional: Bool

    init(title: String, detail: String, action: String,
         grantedNote: String = localised("granted", "разрешено"), optional: Bool = false) {
        self.title = NSTextField(labelWithString: title)
        self.detail = NSTextField(labelWithString: detail)
        self.defaultDetail = detail
        self.defaultAction = action
        self.grantedNote = grantedNote
        self.isOptional = optional
        button = NSButton(title: action, target: nil, action: nil)
        stack = NSStackView()
        super.init(frame: .zero)

        self.title.font = SetupLayout.titleFont
        note.font = SetupLayout.detailFont
        note.textColor = .tertiaryLabelColor
        wantsLayer = true

        self.detail.font = SetupLayout.detailFont
        self.detail.textColor = .secondaryLabelColor
        self.detail.lineBreakMode = .byWordWrapping
        self.detail.maximumNumberOfLines = 3
        self.detail.preferredMaxLayoutWidth = 460

        button.bezelStyle = .rounded
        button.controlSize = .small
        button.target = self
        button.action = #selector(act)

        mark.widthAnchor.constraint(equalToConstant: 18).isActive = true

        let heading = NSStackView(views: [self.title, note])
        heading.orientation = .horizontal
        heading.alignment = .firstBaseline
        heading.spacing = 6

        let text = NSStackView(views: [heading, self.detail])
        text.orientation = .vertical
        text.alignment = .leading
        text.spacing = 2

        for view in [mark, text, SetupLayout.spacer(), button] {
            stack.addArrangedSubview(view)
        }
        stack.orientation = .horizontal
        stack.alignment = .top
        stack.spacing = 10
        stack.edgeInsets = SetupLayout.rowInsets
        stack.translatesAutoresizingMaskIntoConstraints = false
        addSubview(stack)
        NSLayoutConstraint.activate([
            stack.topAnchor.constraint(equalTo: topAnchor),
            stack.bottomAnchor.constraint(equalTo: bottomAnchor),
            stack.leadingAnchor.constraint(equalTo: leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: trailingAnchor),
        ])
        // Every granted row carries one line and they have to look it; a row
        // still explaining itself has to keep the inset under its last line.
        // Both are the same arithmetic every other row gets.
        SetupLayout.fitRowHeight(stack)
    }

    required init?(coder: NSCoder) { fatalError("not used") }

    func tintLayer() {
        layer?.backgroundColor = wantsAttention
            ? NSColor.systemOrange.withAlphaComponent(0.12).cgColor
            : NSColor.clear.cgColor
    }

    override func viewDidChangeEffectiveAppearance() {
        super.viewDidChangeEffectiveAppearance()
        retint()
    }

    @objc private func act() { onAct?() }

    /// Say that something is happening, so a button that takes a second
    /// doesn't look like a button that did nothing.
    func working(_ message: String) {
        button.isEnabled = false
        detail.stringValue = message
    }

    /// The one row the person is being asked to act on right now is tinted.
    /// macOS shows one TCC dialog at a time, so more than one highlighted row
    /// would be pointing at work that cannot be done yet.
    func setAttention(_ on: Bool) {
        wantsAttention = on
        retint()
        title.textColor = on ? .systemOrange : .labelColor
        detail.textColor = on ? .systemOrange : .secondaryLabelColor
        if on {
            mark.image = NSImage(
                systemSymbolName: "exclamationmark.circle",
                accessibilityDescription: localised(
                    "needs your attention", "требует внимания"))
            mark.contentTintColor = .systemOrange
        }
    }

    /// `action` keeps a button on a granted row — for the one permission
    /// macOS will not report, where "granted" is a measurement someone may
    /// reasonably want to take again.
    func update(
        _ state: SetupPermissions.State,
        detail override: String? = nil,
        note noteOverride: String? = nil,
        action actionTitle: String? = nil
    ) {
        button.isEnabled = true
        button.title = actionTitle ?? defaultAction
        detail.stringValue = override ?? defaultDetail

        // A granted permission is one line: the title and how it stands. The
        // reasoning underneath is there to talk someone into granting it, and
        // it has nothing left to say once they have.
        let settled = state == .granted && override == nil
        detail.isHidden = settled || detail.stringValue.isEmpty
        // A row that is down to its title is one line, and sits in the middle
        // of the row like one; a row still explaining itself starts at the
        // top, beside its first line.
        stack.alignment = detail.isHidden ? .centerY : .top
        note.stringValue = noteOverride ?? {
            switch state {
            case .granted: return grantedNote
            case .notAsked, .unknown:
                return isOptional ? localised("optional", "не обязательно") : ""
            case .denied: return ""
            }
        }()
        note.isHidden = note.stringValue.isEmpty

        switch state {
        case .granted:
            mark.image = NSImage(
                systemSymbolName: "checkmark.circle",
                accessibilityDescription: localised("granted", "разрешено"))
            mark.contentTintColor = .systemGreen
            button.isHidden = actionTitle == nil
        case .denied:
            mark.image = NSImage(
                systemSymbolName: "exclamationmark.circle",
                accessibilityDescription: localised("denied", "запрещено"))
            mark.contentTintColor = .systemOrange
            button.isHidden = false
            button.title = localised("Open Settings", "Открыть настройки")
        case .notAsked, .unknown:
            mark.image = NSImage(
                systemSymbolName: "circle.dashed",
                accessibilityDescription: localised("not asked", "не спрашивали"))
            mark.contentTintColor = .tertiaryLabelColor
            button.isHidden = false
        }
    }
}
