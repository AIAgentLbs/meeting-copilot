# Meeting Copilot Capture

Native macOS capture and transcription component for Meeting Copilot by
AI Agent Labs. It captures microphone and system audio without joining the
meeting as a bot and publishes an atomic local transcript snapshot for the
loopback-only copilot UI.

## Build

Requires macOS 15, Xcode command-line tools and Swift 6.

```sh
swift test
make app
```

The application bundle is written to `.build/MeetingCopilotCapture.app`.
Microphone and Screen & System Audio Recording permissions are granted by the
user in macOS System Settings.

## Data

The live transcript is written to:

`~/.local/share/meeting-copilot/meeting-copilot-live.json`

The snapshot contains text and timestamps, not audio or credentials, and is
created with user-only permissions.

