import AppKit

/// AI Agent Labs capture mark: a compact waveform on a rounded field.
/// It stays legible at menu-bar size and changes colour with recorder state.
enum BrandIcon {
    static func color(recording: Bool, paused: Bool) -> NSColor {
        if paused { return .systemOrange }
        if recording { return .systemRed }
        return NSColor(calibratedRed: 0.055, green: 0.255, blue: 0.205, alpha: 1)
    }

    static func image(size: CGFloat, color: NSColor?) -> NSImage {
        let canvas = NSSize(width: size, height: size)
        return NSImage(size: canvas, flipped: false) { rect in
            let field = color ?? self.color(recording: false, paused: false)
            field.setFill()
            NSBezierPath(
                roundedRect: rect.insetBy(dx: size * 0.06, dy: size * 0.06),
                xRadius: size * 0.23,
                yRadius: size * 0.23
            ).fill()

            NSColor.white.setFill()
            let heights: [CGFloat] = [0.26, 0.48, 0.72, 0.48, 0.26]
            let barWidth = max(1, size * 0.075)
            let gap = size * 0.065
            let total = barWidth * CGFloat(heights.count) + gap * CGFloat(heights.count - 1)
            var x = rect.midX - total / 2
            for ratio in heights {
                let height = size * ratio
                let bar = NSRect(x: x, y: rect.midY - height / 2, width: barWidth, height: height)
                NSBezierPath(roundedRect: bar, xRadius: barWidth / 2, yRadius: barWidth / 2).fill()
                x += barWidth + gap
            }
            return true
        }
    }
}
