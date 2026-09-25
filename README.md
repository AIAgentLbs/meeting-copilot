# Meeting Copilot by AI Agent Labs

Private, bot-free live meeting intelligence for macOS. Meeting Copilot captures
your microphone and system audio, keeps a live transcript on your Mac, and lets
Codex check what is being said against the Git repositories and documents you
already have locally.

> Beta. macOS 15+, Apple Silicon. The transcript and repository access remain
> local by default. Codex usage follows the authentication and policy of your
> installed Codex CLI.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/AIAgentLbs/meeting-copilot/main/install.sh | bash
```

Then approve **Microphone** and **Screen & System Audio Recording** when macOS
asks, and run:

```sh
meeting-copilot
```

The local interface opens at `http://127.0.0.1:43121`.

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
