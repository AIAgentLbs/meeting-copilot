import AppKit

/// Shared entry point from setup, the menu bar and recorder controls.
enum AssistantLink {
    @MainActor static func open() {
        NSWorkspace.shared.open(URL(string: "http://127.0.0.1:43121/")!)
    }
}
