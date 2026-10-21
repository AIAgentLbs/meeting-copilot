# Install MeetOnTrack

Download and installation: https://meetontrack.com/.
Russian page: https://meetontrack.com/ru/.

## Mac

Apple Silicon, macOS 15 or later. Capture, Python and helper executables are
included in the package. No compiler, SDK or separate Python is required.

```sh
curl -fsSL https://meetontrack.com/install.sh | bash
```

The command installs the checksum-pinned v0.1.11 archive. Read
[install.sh](install.sh) before running it if desired. An existing installation
must finish its call and quit Capture first. The installer checks again before
replacement and retains timestamped app/web backups.

1. Choose English or Russian on first launch.
2. Approve Microphone and Screen & System Audio Recording for MeetOnTrack in
   macOS settings. Existing installation paths keep the legacy Capture filename.
3. Complete local speech-model setup. Recording and transcription need no paid
   AI key or AI tool account.
4. The installer starts the local service and opens the assistant in your browser
   automatically. Completing setup also opens it. Reopen it anytime with
   **Open MeetOnTrack assistant** at the top of the recorder window or in the
   MeetOnTrack menu-bar menu. No second terminal command is required.
5. Make a short test call and check both sides in the transcript before relying
   on a long meeting. Speaker names can need correction.

The package is a technical beta, ad-hoc signed and not Apple-notarized. If macOS
blocks it, review the exact app in Privacy & Security. Keep Gatekeeper enabled.
Google Chrome is needed for PDF export.

## Windows

Windows 11 24H2 or later, x64. Use PowerShell:

```powershell
irm https://meetontrack.com/install.ps1 | iex
```

The ready-to-run archive includes Capture, .NET, Python and the web assistant.
No compiler or SDK is required. The first setup downloads checksum-verified
local speech models (approximately 1.5 GB). Keep SmartScreen and antivirus
enabled. Finish the call and close Capture before reinstalling.

## Optional AI and context

AI answers use an AI tool you already have: Codex, Claude Code or a local
Ollama. In Getting started, choose the tool, model, effort and speed once;
every AI task uses that choice. The options are read from the installed tool
and your plan, and nothing is preselected. Check AI runs a short test for each
task with that choice. A task the chosen model cannot do is shown unavailable
with the reason, and the other tasks keep working: screenshots are analysed
only when the model accepts images. Relevant
conversation and connected-source excerpts are sent to the chosen AI service. Capture
and local transcription work independently of the AI account.
Git repository search works only with Codex or Claude Code; Ollama cannot read
repositories. Antigravity is detected but cannot be selected yet, because it
cannot be held to read-only, no-tools calls.

Connect local folders in Context sources; Git is optional. Current local formats
are UTF-8 text, Markdown, CSV and source code. Google context is optional and
configured separately in Settings. General local PDF/Office retrieval is not
included in this release.

## Optional report delivery

Settings lets you enable email reports, Google Drive and each delivery channel
separately. Leave them off to keep reports locally.

- SMTP: enter your provider's host, TLS mode, username and app password. Check
  the connection, choose the recipient, enable email and save.
- Google: create your own Desktop OAuth client in your Google Cloud project,
  enable the APIs you need and import its downloaded JSON in Settings. Follow
  the in-app instructions, then sign in to your account. MeetOnTrack does not
  provide a shared Google OAuth application. Connecting does not enable delivery.

Secrets are kept in macOS Keychain or Windows DPAPI. Native usage statistics
have been removed. Delivery errors and manual retry actions are shown in the
assistant. See [delivery setup](docs/DELIVERY.md) for detailed instructions.

## Update

A newer published version produces an in-app indicator with release notes.
Settings also contains the platform-specific update command and a copy button.
Checks run at startup and every 15 minutes while online; they can be disabled.

Finish the call, quit Capture and repeat the installation command. The installer
preserves recordings, settings and model data. Automatic installation is deferred.
An unexpected filesystem/permission failure during replacement may require the
preserved backup. See [updates](docs/UPDATES.md).

## Local files and support

Mac settings: `~/.config/meeting-copilot`. Recordings, reports and the embedded
runtime: `~/.local/share/meeting-copilot`. The installer retains compatibility
paths and never modifies connected repositories.

Windows application versions: `%LOCALAPPDATA%/MeetingCopilot/versions`.
User settings and recordings are outside that application version directory.

For no-audio failures, check permissions on the actual installed application
and selected devices, then reopen Capture. For no PDF, check Chrome. If you
report a problem, include OS, version and a redacted error at
https://github.com/AIAgentLbs/meeting-copilot/issues. Do not upload private
recordings, transcripts, OAuth JSON or delivery credentials.
