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
- Do not enable unattended repository writes until the owner confirms the
  publication policy for private/public and ambiguous meetings.

## Google delivery

The application retries unsent reports and shows recent failures in the UI.
The local `gog` OAuth account must be reconnected before Gmail/Drive delivery
can resume. The retry worker will then process missed reports without resending
ones already marked successful.
