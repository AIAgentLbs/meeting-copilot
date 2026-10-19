import Foundation

// Compatibility entry point. Never regenerate a different legacy app icon.
guard CommandLine.arguments.count == 2 else {
    fatalError("usage: swift scripts/make-icon.swift OUTPUT.icns")
}
let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
let make = Process()
make.executableURL = URL(fileURLWithPath: "/usr/bin/make")
make.arguments = ["-C", root.path, "icon"]
try make.run()
make.waitUntilExit()
guard make.terminationStatus == 0 else { exit(make.terminationStatus) }
let source = root.appendingPathComponent("Resources/MeetingCopilot.icns")
let destination = URL(fileURLWithPath: CommandLine.arguments[1]).standardizedFileURL
if destination != source.standardizedFileURL {
    try Data(contentsOf: source).write(to: destination, options: .atomic)
}
