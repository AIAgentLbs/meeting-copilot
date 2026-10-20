# MeetOnTrack 0.1.11 for Windows

Technical beta for Windows 11 24H2+, x64. Capture, .NET, Python and the web UI
are included; no compiler or SDK is required. Initial setup downloads local
speech models. AI answers are optional and use an AI tool you already have.

- AI tool, model, effort and speed are chosen per task in the web assistant
  (live analysis and chat, live translation, screenshot relevance, summary
  rewrite). The native recorder component is unchanged. Options are discovered from the AI tools installed and signed in on this computer (Codex,
  Claude Code, local Ollama) and from what your plan offers. Nothing is
  hardcoded or preselected. Antigravity is detected but not yet selectable,
  because it cannot be held to read-only, no-tools calls.
- After updating, open Getting started and choose a tool and model for each
  task, then run the check. Until a task has a choice, its AI step is skipped
  with a clear message. Recording and local transcription work without AI.
- Fixed: an old "Install Codex" error saved with a meeting no longer reappears
  after restart once the AI setup has been repaired.

Speech-to-text engine selection is unchanged in this release.

Finish the call and close Capture before installing or updating:

```powershell
irm https://meetontrack.com/install.ps1 | iex
```

Recordings, model data and settings live outside the versioned app directory.
The installer verifies the package checksum. No automatic installer is enabled.

## Build identity

Application source: `effb7a2b65be3cd3e02cc1bfd2be0864340d5ac2`.
Native source: `e733138e2e61d74aac1d03b050624e558e30d155` (its `windows/` tree is
identical to 0.1.10's `b36ee3005e383c5c87ed4bceaf179ee8c95f8bb0`).
ZIP SHA-256: `bc60f21e3c5089781fb1f439fb9cf1a3ce89694e6db0b4acdac1c5e96909fdf8`.
The integrated package version is 0.1.11; its independently versioned native
component retains 0.6.6. The web update checker compares integrated versions.

The native Windows build and core/live regressions passed in GitHub Actions.
Exact package acceptance passed on a Windows runner: 1,734 manifest hashes,
fresh/repeat installation, recording preservation, native metadata, embedded
server self-test, PowerShell syntax and five installer fixtures. Hardware audio is
not tested on the hosted runner.

## Limits

Unsigned technical beta; keep SmartScreen and antivirus enabled. Real-device
audio, permissions, headphone reconnects and installed tray acceptance are not
claimed for this release. Real AI calls through each provider were not
exercised by the release checks; run the Getting started check after choosing.
Test a short call and inspect both sides before relying on a long recording.
Local PDF/Office extraction and optional screen OCR dependencies are not
included. Speaker labels may need correction.
