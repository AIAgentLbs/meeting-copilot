# MeetOnTrack by AI Agent Labs

Private, bot-free live meeting intelligence for macOS. MeetOnTrack captures
your microphone and system audio, keeps a live transcript on your Mac, and lets
Codex check what is being said against the Git repositories and documents you
already have locally.

> Technical beta. macOS 15+, Apple Silicon. Audio/transcript files are stored
> locally; AI analysis can send relevant dialogue and repository excerpts to
> your configured Codex service. Usage follows your CLI account and policy.

## Install

Project page: [English](https://meetontrack.com/) ·
[Русский](https://meetontrack.com/ru/).
The command currently installs the checked, pinned **v0.1.10** package, not
unreleased features from `main`. It requires Apple Silicon, macOS 15+, no separate Python or Apple SDK. Codex is optional for AI answers. Google Chrome
is required for PDF reports. Quit Capture before reinstalling.

v0.1.10 includes the freshly compiled Swift app, the matched web payload and a
source/hash manifest. It is ad-hoc signed, not notarized; automatic installation is deferred; update notifications are included. See [release notes](docs/releases/v0.1.10.md) for scope and gates.

```sh
curl -fsSL https://meetontrack.com/install.sh | bash
```

The installer starts MeetOnTrack and opens the assistant in your browser
automatically, after checking that the local service is ready. Approve
**Microphone** and **Screen & System Audio Recording** and finish model setup
in the native setup window. No second terminal command is needed. Reopen the
page anytime with **Open MeetOnTrack assistant** at the top of the recorder
window or in its menu-bar menu.
See [INSTALL.md](INSTALL.md) for dependencies, first-run permissions, manual
updates and troubleshooting. Automatic in-app updates are not enabled in this
beta. Audio/transcription run locally; AI analysis can send relevant transcript
and repository excerpts through the configured Codex service.

## What it does

- captures meetings without adding a bot to Zoom or Google Meet;
- updates a local near-live transcript with speaker separation where available;
- detects mixed meeting languages and shows an English translation next to
  non-Russian/non-English speech while preserving the original;
- searches up to 15 selected local GitHub or GitLab checkouts without cloning,
  pulling, or modifying them;
- surfaces facts, contradictions, history, risks, commitments, decisions and
  useful questions with file and commit provenance;
- saves manual notes with meeting timecodes, chat, links, services and frames;
- produces local HTML/PDF meeting reports; optional Google Drive, email and
  Telegram delivery is retried after transient failures, and the UI shows
  recent unsent email reports. Email can include the PDF even if Drive fails.

## Privacy model

The web server binds only to `127.0.0.1`. Meeting media, transcript snapshots,
frames and reports are stored under `~/.local/share/meeting-copilot`; settings
and repository manifests are stored under `~/.config/meeting-copilot`. The
installer neither uploads repositories nor runs `git pull`, `fetch`, `clone`,
`checkout`, `reset`, `clean`, `commit` or `push`.
Language detection runs on the Mac. Translation sends only the relevant text
fragments through your authenticated Codex CLI, not raw audio.

## Repository layout

Repository scope (owner decision, 2026-10-19): end-user application software,
installers/updates, tests and user documentation. Website, domain, analytics,
SEO, comparisons and marketing are owned by
[AIAgentLbs/meeting-copilot](https://github.com/AIAgentLbs/meeting-copilot), with
one website backlog in root `SITE_TODO.md`. See `AGENTS.md` for the boundary.

- `capture/` — native macOS audio capture and transcription application.
- `copilot/` — loopback-only UI, repository search and meeting archive.
- `docs/` — application documentation, verification records and release notes.
- `install.sh` — idempotent macOS installer.
- `scripts/windows/install.ps1` — Windows installer used by packaging and CI.

Website pages, comparison/SEO research, analytics and Pages publication live
only in the website repository. Its `planning/2026-10-19-repository-separation.json`
records the verified file transfer. The website keeps its published installer
snapshot; application installer development stays here.

## Development

```sh
python3 copilot/web/server.py --self-test
swift build -c release --package-path capture
```

The AppKit UI test suite additionally requires a logged-in macOS GUI session.
Building the native app requires the macOS 26 SDK; the resulting app keeps a
macOS 15 deployment target.

The release package is built with `scripts/package-release.sh`. Never commit
recordings, transcripts, OAuth profiles, delivery credentials or repository
manifests.

## License

MIT. See [LICENSE](LICENSE) and [capture/THIRD-PARTY-NOTICES.md](capture/THIRD-PARTY-NOTICES.md).
