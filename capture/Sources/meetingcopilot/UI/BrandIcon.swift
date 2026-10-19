import AppKit

/// MeetOnTrack M-and-dot mark, matching the product website.
/// It stays legible at menu-bar size and changes colour with recorder state.
enum BrandIcon {
    static func color(recording: Bool, paused: Bool) -> NSColor {
        if paused { return .systemOrange }
        if recording { return .systemRed }
        return NSColor(calibratedRed: 23/255, green: 76/255, blue: 62/255, alpha: 1)
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

            // Website coordinates are top-down; AppKit's drawing space is bottom-up.
            let mark = NSBezierPath()
            mark.move(to: NSPoint(x: size * 14/64, y: size * 19/64))
            mark.line(to: NSPoint(x: size * 14/64, y: size * 45/64))
            mark.line(to: NSPoint(x: size * 32/64, y: size * 28/64))
            mark.line(to: NSPoint(x: size * 50/64, y: size * 45/64))
            mark.line(to: NSPoint(x: size * 50/64, y: size * 19/64))
            mark.lineWidth = size * 6/64
            mark.lineCapStyle = .round
            mark.lineJoinStyle = .round
            NSColor(calibratedRed: 243/255, green: 244/255, blue: 239/255, alpha: 1).setStroke()
            mark.stroke()
            NSColor(calibratedRed: 220/255, green: 234/255, blue: 227/255, alpha: 1).setFill()
            NSBezierPath(ovalIn: NSRect(x: size * 28/64, y: size * 14/64,
                                       width: size * 8/64, height: size * 8/64)).fill()
            return true
        }
    }
}
