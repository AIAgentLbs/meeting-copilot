# MeetOnTrack 0.1.13 for Windows

Technical beta for Windows 11 24H2+, x64. Capture, .NET, Python and the web UI
are included; no compiler or SDK is required. Initial setup downloads local
speech models. AI answers are optional and use an AI tool you already have.

- Fixed: AI help, the meeting archive and reports failed with "Access is
  denied" for some people. A folder locked that way is moved aside to
  `archive.inaccessible-<time>` or `reports.inaccessible-<time>`, nothing in it
  is read or deleted, and a new folder is made. No administrator rights are
  needed.
- Codex works for a normal user. MeetOnTrack uses the Windows sandbox you set
  up in Codex. If none is set up, Check AI says why Codex refused and what to
  do.
- The AI image check is reliable: it no longer fails because a model named
  the test colour "salmon" or "pink".
- Updating replaces the old version's web server. An old recorder that is
  recording keeps recording; it hands over to the new version once it is
  idle, so an update never cuts a recording. A recorder too old to hand over
  is replaced at the next sign-in. The old versioned sign-in entry is removed;
  the Startup shortcut starts MeetOnTrack.
- A red banner shows anything that blocks recording, the transcript or AI,
  with a button that fixes it or opens the right setting.
- Error messages are plain language instead of technical text.
- "Start new meeting" works whenever audio is recording.
- Removed: the All/Me/Others filter, "Analyse now", the automatic analysis
  checkbox and the Questions/Risks/Decisions tabs.
- The recorder keeps other programs' keys when it saves `config.json`.

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

Application source: `6e809812c3fa30c5a01344a807c4f4b13c1cef4d`.
Native source: `50e7448c880538ab96b57e093b4f7214a7a51de0`
([recorder run 39649348946](https://github.com/AIAgentLbs/meetontrack-recorder/actions/runs/39649348946)).
ZIP SHA-256: `ea182811b10137060cb8c8b331976a318e023efa2491c52b505c25b2cec6e7c9`.
The integrated package version is 0.1.13; its independently versioned native
component retains 0.6.6. The web update checker compares integrated versions.

## Limits

Unsigned technical beta; keep SmartScreen and antivirus enabled. Real-device
audio, permissions, headphone reconnects and installed tray acceptance are not
claimed for this release. Test a short call and inspect both sides before
relying on a long recording. Local PDF/Office extraction and optional screen
OCR dependencies are not included. Speaker labels may need correction.
