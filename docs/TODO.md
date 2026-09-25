# Meeting Copilot delivery follow-up

## Repository meeting history

Requested: after a meeting ends, identify the relevant selected GitHub/GitLab
repository and save a concise meeting history there.

Do not copy the same meeting to every active repository. The current fallback
scope means "search all selected repositories", not "publish to all". Some
meetings have no matching project alias; some projects map to multiple repos.

Acceptance criteria:

- Use the meeting's explicit project/repository choice first. Automatic routing
  is allowed only for one unambiguous project and explicitly permitted private
  destination repositories. Otherwise show a pending routing choice.
- Save a reviewed, project-specific brief under `docs/meetings/` with meeting ID,
  date, decisions, actions and links to the local full report. Never publish raw
  audio, screenshots, transcripts, chat, credentials or a report containing
  unrelated client details.
- Keep private deal economics out of repositories other than the allowlisted
  financial repositories. Do not infer or distribute private amounts.
- Make writes idempotent by meeting ID, show per-repository status in meeting
  history, and verify the remote GitHub/GitLab revision after push. Never claim
  completion from local Git state alone.
- Owner confirmed on 2026-09-25: automatic writes are permitted only to
  verified private repositories for an unambiguous project; ambiguous meetings
  stay pending for selection. The local GitHub and GitLab command-line clients
  currently lack push/API credentials, so unattended publication remains off
  until both the private-visibility check and a real remote push/readback pass.
- Evaluate [Laya](https://github.com/NandhaKishorM/laya) as an optional local
  candidate scorer for one or more repos. It must not independently authorize
  publication: validate on labelled meeting-to-repo examples, calibrate the
  multilingual model, then apply the private-repo and ambiguity gates above.

## Google delivery

The application retries unsent reports and shows recent failures in the UI.
`gog` OAuth is still absent, but the user's existing authorized `gws` client now
serves as a fallback for Gmail and Drive. A completed report from 2026-09-25
was uploaded and delivered through this path, including Telegram and Drive
links. Automatic retries are limited to the most recent three days; older
pending reports need a duplicate check against Sent mail before any backfill.
