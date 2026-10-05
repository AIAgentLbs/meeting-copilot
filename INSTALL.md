# Install Meeting Copilot for Mac

## One command

```sh
curl -fsSL https://aiagentlbs.github.io/meeting-copilot/install.sh | bash
```

[Русская инструкция](https://aiagentlbs.github.io/meeting-copilot/ru/#install).
The page and installer are deployed together through GitHub Pages. You can
read [install.sh](install.sh) before running it. This is a technical public
beta, not a standalone notarized installation or a commercial release.

## Prepare your Mac

- Apple Silicon, macOS 15 or later. Intel and Windows are not supported by this package.
- Python 3.10 or later, available as `python3`.
- Apple Command Line Tools. If absent, run `xcode-select --install` and finish
  the system dialog before running the installation command.
- Codex CLI, installed and authenticated. See the
  [official setup guide](https://developers.openai.com/codex/cli).
- Google Chrome for HTML-to-PDF export; without it, PDF generation is unavailable.
- Internet access for the download, initial model setup and configured cloud AI.

The installer checks the platform, Python, compiler and Codex executable.
Codex account access, model readiness, Chrome and macOS audio permissions still
need first-run checks. It does not install Homebrew or sign into providers.

## What the command installs

Currently **v0.1.8**, from the explicit GitHub Release URL. Its ZIP is verified
against SHA-256:

```text
2575dbe3cae77a0afdddceda1ddb321541ce58b89b9f914dac4a8f6e098fac19
```

This digest was compared with the downloaded ZIP and GitHub asset metadata.
The script stages and compiles three Swift helpers before replacing existing
files. Capture must be closed: installation refuses to stop or replace a
running `MeetingCopilotCapture` process. It checks again after staging.

- App: `/Applications/Meeting Copilot Capture.app`, or `~/Applications` when
  the system Applications directory is not writable.
- Launcher: `~/.local/bin/meeting-copilot`.
- Web UI and helper binaries: `~/.local/share/meeting-copilot`.
- Private settings: `~/.config/meeting-copilot`.
- Web LaunchAgent: `~/Library/LaunchAgents/com.aiagentlbs.meeting-copilot.plist`.

An existing app and web directory are preserved as timestamped backups.
Existing private settings, repository selection and recordings are retained.
The published script and the package are versioned separately: `main` includes
newer work that is not necessarily inside the v0.1.8 download.

## First run

1. Choose English / Русский when the application opens for the first time.
   Interface language is separate from speech and summary language.
2. Approve **Microphone** and **Screen & System Audio Recording** for the exact
   installed Meeting Copilot Capture app in System Settings.
3. Complete model setup in the Capture app and check Codex authentication.
4. Run `~/.local/bin/meeting-copilot`; the UI opens at `http://127.0.0.1:43121`.
   If `~/.local/bin` is already in your PATH, `meeting-copilot` also works.
5. Select the relevant local repositories. Run a short test call, inspect both
   microphone and system audio, and check the saved transcript/report before
   relying on a long recording. Speaker labels can need correction.

Recording and transcription are local. AI analysis may send relevant dialogue
and repository excerpts to the service used by your Codex CLI. Drive, email
and Telegram delivery are optional, require separate configuration and are not
activated by the installer. Fully offline AI and a general model/provider
selector are planned, not promised for this package.

Google context search is optional in Settings and requires a separately
configured `gws` CLI and Google authorization. Calendar, Gmail and Drive are
opt-in, with one account. Drive search currently returns metadata and links.
Native usage statistics are inherited as opt-out, with a visible setup switch;
read [the exact disclosure](capture/docs/analytics.md) before enabling them.
The ZIP includes `release.json` with the runtime source revision and file hashes.

## Updating

Automatic in-app updates are not enabled in this beta. The one-line command
installs the version pinned in `install.sh`; repeating it today reinstalls
v0.1.8. After a new tested release is published, maintainers must update the
script's version and SHA-256 together and deploy the page and script. Then
finish your call, quit Capture and rerun the same command.

Do not use this command to replace a newer development installation with the
older public package. A failed download/checksum/helper compilation leaves the
existing app untouched. Installation is not a full transactional updater:
an unexpected disk/permission failure during file replacement may require
restoring the preserved app/web backups.

## Troubleshooting

- **Capture is running:** finish the meeting and quit Capture using its menu.
  The installer never kills it. Merely closing a web tab is not sufficient.
- **Missing dependency:** follow the exact preflight message and retry; do not
  run the script with `sudo` to work around an unrelated dependency failure.
- **Command not found:** run `~/.local/bin/meeting-copilot` directly.
- **macOS blocks launch:** review the exact downloaded app in Privacy &
  Security. The beta has not completed Developer ID notarization; never
  disable Gatekeeper globally as an installation step.
- **No audio:** check both permission categories for the installed app, then
  quit and reopen Capture. An old backup entry is not the current app.
- **No PDF:** confirm `/Applications/Google Chrome.app` is installed.
- **Need help:** [open an issue](https://github.com/AIAgentLbs/meeting-copilot/issues)
  with OS, app version and a redacted error. Do not upload client recordings,
  transcripts, OAuth credentials or private delivery settings.
