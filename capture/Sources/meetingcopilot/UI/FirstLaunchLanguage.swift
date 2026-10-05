import AppKit

/// Ask before constructing the menu, status and setup windows: their labels
/// are created once, so changing language after construction is too late.
@MainActor
enum FirstLaunchLanguage {
    static func confirmIfNeeded() -> Bool {
        guard InterfaceLanguage.needsFirstLaunchChoice(
            setupPending: SetupState.isPending, configured: Config.interfaceLanguage()
        ) else { return true }
        return choose(suggested: InterfaceLanguage.current)
    }

    /// Labels name themselves in both languages, including on an unsupported
    /// system locale. No speech or summary preference is changed here.
    static func makeAlert(suggested: InterfaceLanguage, savingFailed: Bool = false)
        -> (alert: NSAlert, picker: NSPopUpButton)
    {
        let alert = NSAlert()
        alert.messageText = "Choose your language / Выберите язык"
        alert.informativeText = savingFailed
            ? "Could not save the language. Check access to the settings folder and try again.\n"
                + "Не удалось сохранить язык. Проверьте доступ к папке настроек и повторите."
            : "This is the interface language. Choose the language of your meetings separately in setup.\n"
                + "Это язык интерфейса. Язык речи на встречах выбирается отдельно в настройке."
        alert.addButton(withTitle: "Continue / Продолжить")
        alert.addButton(withTitle: "Quit / Выйти").keyEquivalent = "\u{1b}"

        let picker = NSPopUpButton(frame: NSRect(x: 0, y: 0, width: 320, height: 32))
        for (title, language) in [("English", InterfaceLanguage.english), ("Русский", .russian)] {
            picker.addItem(withTitle: title)
            picker.lastItem?.representedObject = language.rawValue
        }
        picker.selectItem(at: suggested == .english ? 0 : 1)
        picker.setAccessibilityLabel("Interface language / Язык интерфейса")
        alert.accessoryView = picker
        alert.window.initialFirstResponder = picker
        return (alert, picker)
    }

    /// Injection is for isolated acceptance checks, never a second storage
    /// mechanism. A failed save leaves the language and first-run state alone.
    static func choose(
        suggested: InterfaceLanguage,
        save: @MainActor (InterfaceLanguage) -> Bool = {
            Config.update(path: ["interface_language"], value: $0.rawValue)
        },
        present: @MainActor (NSAlert) -> NSApplication.ModalResponse = { $0.runModal() }
    ) -> Bool {
        var selection = suggested
        var savingFailed = false
        while true {
            let (alert, picker) = makeAlert(suggested: selection, savingFailed: savingFailed)
            NSApp.activate(ignoringOtherApps: true)
            guard present(alert) == .alertFirstButtonReturn else { return false }
            guard let code = picker.selectedItem?.representedObject as? String,
                  let selected = InterfaceLanguage(rawValue: code) else { return false }
            selection = selected
            if save(selected) {
                InterfaceLanguage.current = selected
                return true
            }
            savingFailed = true
        }
    }
}
