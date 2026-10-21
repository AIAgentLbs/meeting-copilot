# MeetOnTrack 0.1.14 for Windows

Technical beta for Windows 11 24H2+, x64. Capture, .NET, Python and the web UI
are included; no compiler or SDK is required. Initial setup downloads local
speech models. AI answers are optional and use an AI tool you already have.

- Check AI is reliable for live analysis. Its test file used to sit in a
  temporary folder that the AI tool is not allowed to read, so the check could
  fail although AI worked.

Everything from 0.1.13 is included: no more "Access is denied", Codex in its
own Windows sandbox, the reliable image check, upgrades that never cut a
recording, the red banner and plain error messages.

The speech recognition choice from the Mac release is not available on Windows
yet (MEETONTRACK-69). Getting started says so, and the Windows recorder keeps
transcribing with its local speech models as before.

Finish the call and close Capture before installing or updating:

```powershell
irm https://meetontrack.com/install.ps1 | iex
```

Version 0.1.10 and 0.1.11 do not show this update in the app: the project's
GitHub address changed, and those versions reject release pages at the new
address. Run the command above once. Version 0.1.12 and later check the new
address.

Recordings, model data and settings live outside the versioned app directory.
The installer verifies the package checksum. No automatic installer is enabled.

## Build identity

Application source: `5aaaec8ec3e5bfad28929e4f0dc9262ec706a375`.
Native source: `50e7448c880538ab96b57e093b4f7214a7a51de0`
([recorder run 39649348946](https://github.com/AIAgentLbs/meetontrack-recorder/actions/runs/39649348946)).
ZIP SHA-256: `8f49ad1eb30172b04e12e9f3e8ac447bdba6f6860797e77d2681b5fa9212e2bb`.
The integrated package version is 0.1.14; its independently versioned native
component retains 0.6.6. The web update checker compares integrated versions.

## Limits

Unsigned technical beta; keep SmartScreen and antivirus enabled. Real-device
audio, permissions, headphone reconnects and installed tray acceptance are not
claimed for this release. Test a short call and inspect both sides before
relying on a long recording. Local PDF/Office extraction and optional screen
OCR dependencies are not included. Speaker labels may need correction.
