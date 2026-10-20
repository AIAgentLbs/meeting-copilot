# New meeting within continuous recording

Status: approved, implemented and installed on Mac on 2026-10-13. Verified with
161 Python tests and real-browser synthetic cancellation/retry/history checks.
No real boundary was applied to the owner's call; native Capture was unchanged.

## Approved intent

The owner wants a button that begins an independent meeting at the moment of
activation without stopping or restarting audio capture. The previous meeting
must remain available in history, with its own transcript, questions, risks,
decisions, notes, screenshots and chat. The new meeting must not inherit the
old meeting's analysis. The existing New context button does not do this.

## Selected approach

Keep the native Capture session and original audio files unchanged. Persist
logical meeting boundaries in the local application data directory, not Git.
Each logical meeting has an independent ID and a half-open time interval over
the original recording: [start, end). The active interval has no end yet.
History shows independent meetings, each referencing the original recording
and its own audio time range. Do not imply there are already independent audio
files: creating separate audio exports is a downstream export operation.

This avoids reopening microphone/system-audio taps, interrupting recognition,
or deploying a new native executable during the owner's active call.

## Boundary operation

- Add a separate Start new meeting from now button. Its visible explanation
  says that it preserves the current meeting and continues audio recording.
- Confirm the operation in a dialog; allow an optional title, with a usable
  default. Cancellation performs no write.
- Submit the expected current logical meeting ID and an idempotency token.
  The server chooses the boundary timestamp. Reject a stale ID, an inactive
  recorder or an ambiguous recorder identity with a visible explanation.
- Persist the previous interval end and new interval start as one atomic
  operation. Preserve the first interval under the original meeting ID.
- Confirm success only after persistence; return the new meeting ID and title.
  Duplicate submission returns the same result, never a second boundary.
- Refresh the current view and reset signatures for transcript, journal,
  chat, frames and call plan. Show an explicit success message and preserve
  the panels' layout and interface language.

## Data routing and consistency

- Keep the physical capture ID separate from the logical meeting ID. Recording
  health, recovery and recognition-resume commands use the physical ID.
- Apply the logical interval before transcript consumers assemble AI context.
  Future recognized speech is assigned by its audio timestamp, not arrival
  time. Late results before a boundary update the previous meeting in history.
- A segment crossing a boundary belongs to the interval containing its start
  timestamp and is marked as spanning the boundary. Do not duplicate, discard
  or claim word-level splitting when the recognizer supplies no word timing.
- Route newly captured screenshots and imported chat using their event times;
  manual notes use the current logical ID. Preserve provenance and originals.
- AI jobs retain the logical ID and interval captured when they began. An old
  result may finish in the previous meeting, never in the new meeting's map.
  A new logical meeting starts with a fresh AI thread/context. Do not clear a
  busy global session or permit automatic analysis to reuse its old thread.
- Preserve manual speaker corrections by stable original segment identity;
  filtering must not invalidate existing corrections.
- Archive snapshots retain physical recording identity, logical interval and
  explicit owner-created boundary metadata. Disable continuous-chain merging
  across those boundaries, even if titles and recording directories match.
- Report generation, export and delivery must use only the selected interval.
  Do not attach/link the entire original audio as if it were that meeting's
  isolated audio. Until bounded audio export exists, disclose the audio range
  locally and omit unbounded audio from external meeting delivery.
- Load boundaries after a web-service restart. Native recording stop closes
  only the last logical interval; archive and report all intervals separately.
  A subsequent physical recording starts an independent first interval.

## Implementation surfaces

Add a small persisted boundary store and deterministic interval projection.
Integrate it at TranscriptState snapshots and the archive/report boundary.
Add a dedicated HTTP endpoint and UI control rather than repurposing AI reset.
Reuse existing archive, journal and meeting history consumers where possible.
No Google scopes, new accounts, dependencies or transcript copies in Git.

## Verification and deployment gates

Use synthetic data only. First add failing regressions for two and three
successive boundaries, delayed ASR, boundary-crossing segments, idempotency,
stale requests, persistence failure, service restart, physical recorder stop,
old AI jobs finishing late, independent report context and archive non-merging.
Verify health/recovery still targets the physical session and that creating a
boundary never invokes native record stop/start/resume or changes audio files.

Test the UI confirmation, cancellation, optional title, visible errors and
success with the application's supported languages. Inspect the actual UI.
Before updating the installed web service, reconcile its differences from the
repository so existing owner fixes are preserved. Capture must not restart.
If a web-only deployment is safe, verify audio growth before and after it and
that the existing transcript remains readable. Never test a real boundary on
the owner's call without an explicit request to apply that boundary now.

## Scope exclusions

Do not retroactively divide past meetings, invent missing speech, restart
Capture, or publish a package before the feature and relevant tests pass.
Do not add a second recording system. Separate bounded audio exports must use
the persisted interval and must not silently share other meetings' audio.
