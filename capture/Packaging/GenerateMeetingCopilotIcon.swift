import AppKit
import Foundation

guard CommandLine.arguments.count == 2 else {
    fatalError("usage: swift GenerateMeetingCopilotIcon.swift OUTPUT.iconset")
}

let output = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)

func png(size: Int, name: String) throws {
    let side = CGFloat(size)
    guard let bitmap = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: size,
        pixelsHigh: size,
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0,
        bitsPerPixel: 0
    ), let context = NSGraphicsContext(bitmapImageRep: bitmap)
    else { fatalError("could not create bitmap for \(name)") }
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = context
    defer { NSGraphicsContext.restoreGraphicsState() }

    NSColor(calibratedRed: 0.055, green: 0.255, blue: 0.205, alpha: 1).setFill()
    NSBezierPath(
        roundedRect: NSRect(x: side * 0.04, y: side * 0.04, width: side * 0.92, height: side * 0.92),
        xRadius: side * 0.22,
        yRadius: side * 0.22
    ).fill()

    NSColor.white.setFill()
    let heights: [CGFloat] = [0.26, 0.48, 0.72, 0.48, 0.26]
    let barWidth = max(1, side * 0.075)
    let gap = side * 0.065
    let total = barWidth * CGFloat(heights.count) + gap * CGFloat(heights.count - 1)
    var x = side / 2 - total / 2
    for ratio in heights {
        let height = side * ratio
        let rect = NSRect(x: x, y: side / 2 - height / 2, width: barWidth, height: height)
        NSBezierPath(roundedRect: rect, xRadius: barWidth / 2, yRadius: barWidth / 2).fill()
        x += barWidth + gap
    }

    context.flushGraphics()
    guard let data = bitmap.representation(using: .png, properties: [:])
    else { fatalError("could not render \(name)") }
    try data.write(to: output.appendingPathComponent(name), options: .atomic)
}

let files = [
    (16, "icon_16x16.png"), (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"), (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"), (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"), (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"), (1024, "icon_512x512@2x.png"),
]
for (size, name) in files { try png(size: size, name: name) }
