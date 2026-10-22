# MeetOnTrack 0.1.15 for Windows

Technical beta for Windows 11 24H2+, x64. Capture, .NET, Python and the web UI
are included; no compiler or SDK is required. Initial setup downloads local
speech models. AI answers are optional and use an AI tool you already have.

- The report delivery button says what is wrong and what to do: "Report for
  'Weekly sync' on October 16 was not sent" with one Send again button, "may
  not have arrived" when it is unknown, or "Email: sign in again" leading
  straight to Settings. Failures that were already fixed no longer show.
- A damaged report status file repairs itself. If the report file itself is
  gone, the button offers to create the report again.
- A cleaner main screen: the interface language moved to Settings, the helper
  lines under the buttons are gone, and the live transcript can be hidden and
  shown again. These choices are remembered.

Everything from 0.1.14 is included. Zoom speaker names per phrase are part of
the Mac release; the Windows package does not include the image libraries
they need.

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

Application source: `257290040162954e0677813ce9442ead5004ed17`.
Native source: `50e7448c880538ab96b57e093b4f7214a7a51de0`
([recorder run 39649348946](https://github.com/AIAgentLbs/meetontrack-recorder/actions/runs/39649348946)).
ZIP SHA-256: `cf7a9a5062ff0683b89316e9496be640e42fd4578087d8630546d1880245f63b`.
The integrated package version is 0.1.15; its independently versioned native
component retains 0.6.6. The web update checker compares integrated versions.

## Limits

Unsigned technical beta; keep SmartScreen and antivirus enabled. Real-device
audio, permissions, headphone reconnects and installed tray acceptance are not
claimed for this release. Test a short call and inspect both sides before
relying on a long recording. Local PDF/Office extraction and optional screen
OCR dependencies are not included. Speaker labels may need correction.
