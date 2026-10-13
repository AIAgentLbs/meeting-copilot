# Meeting Copilot delivery follow-up

## Existing UI accessibility warnings

- Verify the existing muted-text contrast and dialog content padding in
  `copilot/web/styles.css` with actual light/dark UI screenshots and computed
  styles. The Impeccable scan during removal of AI chat reset flagged these
  unrelated areas; they were not changed in that scoped task. Adjust verified
  failures without altering the recording or meeting-context workflows.

## Continuous recording meeting boundaries

- Implement the owner's requested Start new meeting from now action without
  restarting Capture. Persist independent logical meeting intervals over the
  original audio; isolate transcript, AI jobs/context, journal, screenshots,
  chat, reports and history. Prevent archive continuous-chain merging across
  explicit boundaries and keep recovery targeting the physical recording ID.
  Owner requested implementation on 2026-10-13; implementation plan awaits review:
  [2026-10-13 continuous meeting boundary specification](superpowers/specs/2026-10-13-continuous-meeting-boundary-design.md).
  [Implementation plan](superpowers/plans/2026-10-13-continuous-meeting-boundary.md).
  Product implementation and live installation are not yet completed.

## Windows beta acceptance gaps

- Keep the full Python suite platform-aware: three security tests currently
  assume POSIX mode 0600, and a recorder test assumes POSIX path spelling.
  Windows ACL checks must replace, not silently skip, the security assertions.
- Optional screen OCR/active-tile detection requires Pillow and NumPy, not
  shipped in the minimal embedded Python package. Do not claim that feature
  works on Windows until dependencies and an actual UI test are included.
- Add packaged-application audio and recognition-resume smoke testing to the
  release gate, in addition to native unit tests and installer fixture tests.
- Verify extended real-call reconnects and report/PDF/delivery parity before
  promoting the unsigned Windows technical beta to a stable release.
- Add signed distribution and a verified in-app update mechanism. The current
  beta updates by re-running the published installer after finishing the call.

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
