# Meeting Copilot by AI Agent Labs

Private, bot-free live meeting intelligence for macOS. Meeting Copilot captures
your microphone and system audio, keeps a live transcript on your Mac, and lets
Codex check what is being said against the Git repositories and documents you
already have locally.

> Technical beta. macOS 15+, Apple Silicon. Audio/transcript files are stored
> locally; AI analysis can send relevant dialogue and repository excerpts to
> your configured Codex service. Usage follows your CLI account and policy.

## Install

Project page: [English](https://aiagentlbs.github.io/meeting-copilot/) ·
[Русский](https://aiagentlbs.github.io/meeting-copilot/ru/).
The command currently installs the checked, pinned **v0.1.9** package, not
unreleased features from `main`. It requires Apple Silicon, macOS 15+, Python
3.10+, Apple Command Line Tools and an authenticated Codex CLI. Google Chrome
is required for PDF reports. Quit Capture before reinstalling.

v0.1.9 includes the freshly compiled Swift app, the matched web payload and a
source/hash manifest. It is ad-hoc signed, not notarized; automatic updates
remain disabled. See [release notes](docs/releases/v0.1.9.md) for scope and gates.

```sh
curl -fsSL https://aiagentlbs.github.io/meeting-copilot/install.sh | bash
```

Then approve **Microphone** and **Screen & System Audio Recording** when macOS
asks, and run:

```sh
~/.local/bin/meeting-copilot
```

The local interface opens at `http://127.0.0.1:43121`.
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

- `capture/` — native macOS audio capture and transcription application.
- `copilot/` — loopback-only UI, repository search and meeting archive.
- `docs/` — product site published with GitHub Pages.
- `install.sh` — idempotent macOS installer.

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
