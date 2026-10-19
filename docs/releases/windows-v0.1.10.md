# MeetOnTrack 0.1.10 for Windows

Technical beta for Windows 11 24H2+, x64. Capture, .NET, Python and the web UI
are included; no compiler or SDK is required. Initial setup downloads local
speech models. AI answers optionally use your own Codex account and its limits.

- MeetOnTrack native identity and M icon, including tray and installed executable.
- Clear first-run setup, optional AI readiness check and connected local folders.
- Meeting history, timed notes and meeting analysis in the local assistant.
- Optional SMTP or your own Google Desktop OAuth JSON for report delivery.
- Optional Calendar/Gmail/Drive context, controlled separately from delivery.
- New-version indicator, release notes and a copyable manual update command.
- No usage-statistics control or telemetry implementation.

Finish the call and close Capture before installing or updating:

```powershell
irm https://meetontrack.com/install.ps1 | iex
```

Recordings, model data and settings live outside the versioned app directory.
The installer verifies the package checksum. No automatic installer is enabled.

## Build identity

Application source: `ae27f2b8a323a1b7d20db3a6ef23e1345cb4249b`.
Native source: `b36ee3005e383c5c87ed4bceaf179ee8c95f8bb0`.
ZIP SHA-256: `3126a3fc819bb80d1ddd762ce14310d42bf99ae3b974983f0872fdcff39026c9`.
The integrated package version is 0.1.10; its independently versioned native
component retains 0.6.6. The web update checker compares integrated versions.

The native Windows build and core/live regressions passed in GitHub Actions.
Exact package acceptance passed on a Windows runner: 1,728 manifest hashes,
fresh/repeat installation, recording preservation, native metadata, embedded
server self-test, PowerShell syntax and five installer fixtures. Hardware audio
is not tested on the hosted runner.

## Limits

Unsigned technical beta; keep SmartScreen and antivirus enabled. The owner's
physical Windows host was offline during this release, so real-device audio,
permissions, headphone reconnects and installed tray acceptance are not claimed.
Test a short call and inspect both sides before relying on a long recording.
Local PDF/Office extraction and optional screen OCR dependencies are not included.
Speaker labels may need correction. Provider consent and SMTP configuration
must be checked using the user's chosen account.
