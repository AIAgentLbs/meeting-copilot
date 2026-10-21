# MeetOnTrack 0.1.12 for Windows

Technical beta for Windows 11 24H2+, x64. Capture, .NET, Python and the web UI
are included; no compiler or SDK is required. Initial setup downloads local
speech models. AI answers are optional and use an AI tool you already have.

- Choose the AI once. In Getting started, pick the tool, model, effort and
  speed one time, and every AI task in the web assistant uses that choice: live
  analysis and chat, live translation, screenshot relevance and summary
  rewrite. If 0.1.11 had the same choice for every task, it is kept. A task
  the chosen model cannot do is shown as unavailable with the reason, and the
  other tasks keep working.
- Call audio is labelled "Others" ("Остальные" in Russian) in the web
  transcript. Your own microphone stays "You".
- Fixed: live translations of a finished meeting are kept when the service
  restarts.

The speech recognition choice from the Mac release is not available on Windows
yet. Getting started says so, and the Windows recorder keeps transcribing with
its local speech models as before. The native recorder component is unchanged.

Finish the call and close Capture before installing or updating:

```powershell
irm https://meetontrack.com/install.ps1 | iex
```

Version 0.1.10 and 0.1.11 do not show this update in the app: the project's
GitHub address changed, and those versions reject release pages at the new
address. Run the command above once. Version 0.1.12 checks the new address.

Recordings, model data and settings live outside the versioned app directory.
The installer verifies the package checksum. No automatic installer is enabled.

## Build identity

Application source: `775ac309bca9d116a7d51b5f8f52e2538716eb38`.
Native source: `e733138e2e61d74aac1d03b050624e558e30d155` (its `windows/` tree is
identical to 0.1.10's `b36ee3005e383c5c87ed4bceaf179ee8c95f8bb0`).
ZIP SHA-256: `6618f0239155a6e5d46fb2e6a29c28ee48a809e9aa9edce6ad943ec90c648e0b`.
The integrated package version is 0.1.12; its independently versioned native
component retains 0.6.6. The web update checker compares integrated versions.

The Mac 0.1.12 package was built from `84d5aaa`. The Windows package adds one
Windows-only change on top: the web server no longer starts the recorder to
list speech options, because the Windows recorder does not have that command
yet and would open its window instead.

Exact package acceptance passed on a Windows runner: 1,740 manifest hashes,
fresh/repeat installation, recording preservation, native metadata, embedded
server self-test, PowerShell syntax and five installer fixtures. Hardware audio
is not tested on the hosted runner.

## Limits

Unsigned technical beta; keep SmartScreen and antivirus enabled. Real-device
audio, permissions, headphone reconnects and installed tray acceptance are not
claimed for this release. Real AI calls through each provider were not
exercised by the release checks; run the Getting started check after choosing.
Test a short call and inspect both sides before relying on a long recording.
Local PDF/Office extraction and optional screen OCR dependencies are not
included. Speaker labels may need correction.
