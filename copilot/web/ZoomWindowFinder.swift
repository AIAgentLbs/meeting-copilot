import CoreGraphics
import Foundation

struct Window: Codable {
    let id: Int
    let owner: String
    let title: String
    let layer: Int
    let x: Int
    let y: Int
    let width: Int
    let height: Int
}

let raw = CGWindowListCopyWindowInfo(
    [.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID
) as? [[String: Any]] ?? []

let candidates: [(score: Int, window: Window)] = raw.enumerated().compactMap { index, item in
    let layer = item[kCGWindowLayer as String] as? Int ?? -1
    let id = item[kCGWindowNumber as String] as? Int ?? 0
    let owner = item[kCGWindowOwnerName as String] as? String ?? ""
    let title = item[kCGWindowName as String] as? String ?? ""
    let bounds = item[kCGWindowBounds as String] as? [String: Any] ?? [:]
    let x = Int(bounds["X"] as? Double ?? 0)
    let y = Int(bounds["Y"] as? Double ?? 0)
    let width = Int(bounds["Width"] as? Double ?? 0)
    let height = Int(bounds["Height"] as? Double ?? 0)
    guard (0...3).contains(layer), id > 0, width >= 300, height >= 200,
          !title.localizedCaseInsensitiveContains("Meeting Copilot")
    else { return nil }

    var score = 0
    if title.contains("🔊") { score += 120 }
    if owner.localizedCaseInsensitiveContains("zoom") { score += 100 }
    if title.localizedCaseInsensitiveContains("zoom") { score += 80 }
    if owner.localizedCaseInsensitiveContains("google chrome") {
        score += 20
        // Chrome exposes its web-meeting picture-in-picture surface as a
        // small layer-3 window. Prefer it over the main Chrome window: the
        // latter may only carry an audio glyph from a background Zoom tab
        // while visibly showing an unrelated site.
        let isPictureInPicture = layer > 0 && width <= 900 && height <= 700
        if isPictureInPicture { score += 240 }
        // CGWindowList is front-to-back. When Zoom's web client title has no
        // Zoom word or audio glyph, prefer the foremost large Chrome meeting
        // window after excluding Meeting Copilot itself.
        score += max(0, 20 - index)
    }
    guard score >= 20 else { return nil }
    return (score, Window(id: id, owner: owner, title: title, layer: layer,
                          x: x, y: y, width: width, height: height))
}

if CommandLine.arguments.contains("--all") {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    let data = try encoder.encode(candidates.map(\.window)) + Data("\n".utf8)
    FileHandle.standardOutput.write(data)
} else if let best = candidates.max(by: { $0.score < $1.score })?.window {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.sortedKeys]
    let data = try encoder.encode(best) + Data("\n".utf8)
    if CommandLine.arguments.count == 3, CommandLine.arguments[1] == "--write" {
        let destination = URL(fileURLWithPath: CommandLine.arguments[2])
        try data.write(to: destination, options: .atomic)
        try FileManager.default.setAttributes(
            [.posixPermissions: 0o600], ofItemAtPath: destination.path)
    } else {
        FileHandle.standardOutput.write(data)
    }
} else {
    exit(1)
}
