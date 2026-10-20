# Continuous Meeting Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Start an independent meeting from now while preserving uninterrupted native recording and the previous meeting in history.

**Architecture:** Keep native physical recording identity unchanged. A small atomic local boundary store projects physical events into independent logical intervals before archive, UI and AI consumers see them. Explicit boundaries prevent archive auto-merging and prevent old AI jobs from contaminating the new map.

**Tech Stack:** Existing Python standard-library web service, unittest, browser JavaScript/CSS; no new dependencies or native Capture changes.

**Spec:** `docs/superpowers/specs/2026-10-13-continuous-meeting-boundary-design.md`

## Global Constraints

- Keep the native Capture session and original audio files unchanged.
- Persist logical meeting boundaries in the local application data directory, not Git.
- Each logical meeting has an independent ID and a half-open time interval over the original recording: [start, end).
- Preserve the first interval under the original meeting ID.
- Future recognized speech is assigned by its audio timestamp, not arrival time.
- Do not duplicate, discard or claim word-level splitting when the recognizer supplies no word timing.
- Recording health, recovery and recognition-resume commands use the physical ID.
- An old result may finish in the previous meeting, never in the new meeting's map.
- Disable continuous-chain merging across those boundaries, even if titles and recording directories match.
- Until bounded audio export exists, disclose the audio range locally and omit unbounded audio from external meeting delivery.
- No Google scopes, new accounts, dependencies or transcript copies in Git.
- Capture must not restart.
- Never test a real boundary on the owner's call without an explicit request to apply that boundary now.
- Do not reintroduce the removed AI-chat reset control or `/api/reset` endpoint.

## Review Focus

1. Lost HTTP response followed by retry: same token returns the same new ID, including after restart (Task 1).
2. Two tabs race: exactly one boundary succeeds; stale expected ID conflicts visibly (Tasks 1 and 4).
3. Disk write failure or corrupt store: no apparent successful split or silent loss of boundaries (Task 1).
4. Late recognition and AI completion: old content remains in the old meeting, including crossing segments and speaker corrections (Tasks 2 and 3).
5. Finished recording or different physical session: close the correct last interval and never carry its offsets into the next session (Tasks 1 and 3).

## File Responsibilities

- Create `copilot/web/meeting_boundaries.py`: local persistence, validation, idempotency and deterministic projection only.
- Create `copilot/web/test_meeting_boundaries.py`: synthetic interval/store regressions.
- Modify `copilot/web/archive.py`: interval-aware history, reports, event association and audio disclosure.
- Create `copilot/web/test_logical_meeting_archive.py`: isolated archive/report regressions.
- Modify `copilot/web/server.py`: endpoint, projection/cache wiring, physical recovery mapping and AI job ownership.
- Create `copilot/web/test_logical_meeting_server.py`: loopback endpoint and AI race tests.
- Modify `copilot/web/index.html`, `app.js`, `styles.css`: explicit split control, confirmation and status feedback.
- Create `copilot/web/test_meeting_boundary_ui.py`: UI contract regression.
- Modify `docs/TODO.md`: feature status and any remaining bounded-audio export limitation.

All new tests use temporary directories and synthetic speech, never real meeting text. Run shell commands through `/opt/homebrew/bin/rtk proxy`, in this checkout.

### Task 1: Durable boundaries and projection

**Files:** Create `copilot/web/meeting_boundaries.py`, `copilot/web/test_meeting_boundaries.py`.

**Interfaces:**
- `MeetingBoundaries(path: Path)` loads a versioned JSON store, guarded by an RLock.
- `split(physical: dict, expected_id: str, token: str, title: str, boundary_at: str) -> dict` returns `{meeting_id, physical_meeting_id, title, started_at}`. Caller supplies an ISO UTC server timestamp. Raise `BoundaryConflict` for stale identity, `BoundaryUnavailable` for inactive/ambiguous recording; persistence errors propagate without mutating memory.
- `project(physical: dict) -> list[dict]` returns ordered snapshots carrying `physical_meeting_id`, `logical_interval: {start, end}`, `explicit_boundary: bool`, `audio_range: {start_seconds, end_seconds}` and original native fields. Without a boundary, return the original snapshot augmented with physical identity.
- `revision: int` increments after a committed store change and participates in annotation cache keys.
- Persist only IDs, titles, timestamps, tokens and interval metadata; no speech or secrets. Write temporary sibling, flush/fsync, atomic replace; publish new in-memory state only afterward. Validate loaded schema and ordered nonoverlapping intervals; corrupt data fails closed.

- [ ] Write the first failing test:

```python
def test_split_preserves_first_id_and_retries_after_restart(self):
    physical = {"meeting_id": "p1", "meeting": "Example", "status": "recording",
                "started_at": "2026-01-01T10:00:00Z", "segments": []}
    store = MeetingBoundaries(self.path)
    result = store.split(physical, "p1", "request-1", "Second", "2026-01-01T10:05:00Z")
    retry = MeetingBoundaries(self.path).split(
        physical, "p1", "request-1", "Second", "2026-01-01T10:06:00Z")
    self.assertEqual(result, retry)
    parts = store.project(physical)
    self.assertEqual([p["meeting_id"] for p in parts], ["p1", result["meeting_id"]])
    self.assertEqual(parts[0]["logical_interval"]["end"], parts[1]["logical_interval"]["start"])
```

- [ ] Run `python3 -m unittest discover -s copilot/web -p test_meeting_boundaries.py -v`; expect missing module/interface failure.
- [ ] Implement the interfaces with UUID logical IDs. Check a saved token before stale-ID validation so retries work after success; reject reuse of a token with different physical ID/title/expected ID. Bound token length to 128 characters and title to 200. Serialize validation and atomic commit under the same lock. Implement projection by segment start timestamp, preserving original identity as `original_segment_id` and marking crossing segments `spans_boundary: true`.
- [ ] Add synthetic tests with explicit assertions: three splits yield four ordered intervals; two concurrent calls with different tokens and the same expected ID yield one success/one conflict; mocked `os.replace` failure leaves disk and memory unchanged; malformed store raises rather than returning an empty store; delayed pre-boundary speech occurs only in the first interval; crossing speech occurs exactly once; next physical ID projects unchanged; physical finish closes only its final interval at native end time. Unknown/unparseable event times must remain preserved with visible unassigned provenance, not silently dropped or assigned to the new meeting.
- [ ] Run the same test command and require all tests pass; inspect persisted JSON to confirm no `segments` or speech strings.
- [ ] Commit only these two files with `feat: persist logical meeting boundaries`.

### Task 2: Archive, events and report isolation

**Files:** Modify `copilot/web/archive.py`; create `copilot/web/test_logical_meeting_archive.py`.

**Interfaces:** Consumes Task 1 projected snapshot fields. `MeetingArchive.sync_transcript(transcript: dict)` continues its existing signature; `detail(meeting_id: str)` and `report_detail(meeting_id: str)` return logical time bounds and physical identity. Existing non-partitioned archives remain compatible.

- [ ] Write a regression using a temporary MeetingArchive and two projected snapshots of one physical recording, both titled `Example`:

```python
def test_explicit_boundary_prevents_report_merge(self):
    for part in self.parts:
        self.archive.sync_transcript(part)
    first = self.archive.report_detail(self.parts[0]["meeting_id"])
    second = self.archive.report_detail(self.parts[1]["meeting_id"])
    self.assertEqual(first["source_meeting_ids"], [self.parts[0]["meeting_id"]])
    self.assertEqual(second["source_meeting_ids"], [self.parts[1]["meeting_id"]])
    self.assertNotEqual(first["transcript"]["segments"], second["transcript"]["segments"])
```

- [ ] Run `python3 -m unittest discover -s copilot/web -p test_logical_meeting_archive.py -v`; require the merge regression fails before changing archive behavior.
- [ ] Persist physical ID, interval and explicit boundary metadata in archive snapshots. Derive logical start/end/duration from intervals ahead of recording metadata. Prevent `_continuous_chain` crossing either side of an explicit boundary. Do not let the previous longer-segment fallback restore physical/unfiltered content into a logical snapshot. Preserve manual speaker edits by original segment identity, with fallback compatibility for legacy edits.
- [ ] Route physical screenshots and imported chat by event timestamp into logical detail views without duplicating source files; manual notes retain their submitted logical ID. Unknown timestamps remain visible as unassigned, not relabeled as known. `detail()` exposes original audio range locally; partitioned `report_detail()` removes whole-recording attachment/link fields used by delivery and adds a plain explanation of the bounded-audio omission. Report eligibility must allow a closed logical interval despite the physical recorder still being active; refresh reports when late ASR changes a closed interval.
- [ ] Add tests asserting: old late speech updates only its archive; note, screenshot and chat ownership stays correct; edited speaker identity survives projection; physical duration does not overwrite logical duration; old/new report text contains only its own synthetic sentence; partitioned external report payload has no whole-recording audio path/link; legacy unpartitioned report merging still passes.
- [ ] Run this test module plus existing archive/delivery tests via unittest discovery; commit `feat: isolate logical meeting archives and reports`.

### Task 3: HTTP boundary and in-flight AI ownership

**Files:** Modify `copilot/web/server.py`; create `copilot/web/test_logical_meeting_server.py`.

**Interfaces:** Consumes `MeetingBoundaries.split`, `project`, `revision`. Produces `POST /api/meeting/new` with JSON `{expected_meeting_id, request_id, title}`; response 200 is Task 1 split result. Use existing host/origin and body limits. Return 409 on stale ID, 409 when recorder identity cannot safely split, and 500 on persistence failure. Native health truth, not ASR freshness, determines recording activity.

- [ ] Write loopback HTTP test modeled on `test_removed_chat_reset.py`, with synthetic native snapshot and mocked native controls:

```python
def test_split_does_not_control_native_recorder(self):
    result = self.post_new(expected_meeting_id="p1", request_id="one", title="Second")
    self.assertEqual(result.status, 200)
    self.native_stop.assert_not_called()
    self.native_start.assert_not_called()
    self.native_resume.assert_not_called()
    self.assertEqual(self.state()["transcript"]["physical_meeting_id"], "p1")
```

The fixture helpers start/stop a temporary ThreadingHTTPServer, replace module globals temporarily and return parsed bounded synthetic API state; never contact installed port 43121.

- [ ] Run `python3 -m unittest discover -s copilot/web -p test_logical_meeting_server.py -v`; expect 404 before endpoint implementation.
- [ ] Keep raw physical snapshot available internally. Project before annotation/AI/UI consumers; archive loop syncs every projected interval so delayed recognition refreshes closed meetings. Include store revision and logical ID in annotation caches. Translate logical IDs to physical IDs for recognition resume and health checks; never replace native files or health observer identity. Persist/load store under local application data on startup.
- [ ] Capture logical ID, interval and thread ownership before each AI job begins. Its messages/map/journal results are written under that captured ID. On a boundary, a busy old job may complete, but new analysis waits until the old global worker releases; then bind a fresh thread to the new logical ID. Do not clear chat history or reuse an old thread for new context. Return visible pending analysis state while occupied.
- [ ] Add tests: old AI job paused at a threading.Event, split, release job, assert no old signals/new-map pollution; new request starts fresh thread; inactive/ambiguous recorder rejects; stale tab rejects; duplicate request after simulated server restart returns same ID; health/resume still uses physical ID; recording stop closes final interval; invalid origin rejects with no writes. Guard physical identity against a recorder change between endpoint read and commit.
- [ ] Run server tests and `python3 -m unittest discover -s copilot/web -p 'test_*.py'`; commit `feat: start logical meetings without restarting capture`.

### Task 4: Explicit user control and feedback

**Files:** Modify `copilot/web/index.html`, `app.js`, `styles.css`; create `copilot/web/test_meeting_boundary_ui.py`.

**Interfaces:** Calls Task 3 endpoint. Uses logical `meeting_id` for expected identity; stores a single request token per pending operation and retains it through ambiguous network retries. UI uses existing RU/EN translation pattern, external JS and the current self-only CSP.

- [ ] Write UI contract test:

```python
def test_split_control_is_not_chat_reset(self):
    html = (self.root / "index.html").read_text()
    js = (self.root / "app.js").read_text()
    self.assertIn('id="new-meeting-button"', html)
    self.assertIn('/api/meeting/new', js)
    self.assertNotIn('/api/reset', js)
    self.assertIn('Начать новую встречу', js)
    self.assertIn('Start new meeting', js)
```

- [ ] Run `python3 -m unittest discover -s copilot/web -p test_meeting_boundary_ui.py -v`; expect missing control failure.
- [ ] Add `new-meeting-button` in meeting controls, enabled only when native audio recording is confirmed. Visible explanation: RU `Сохранит текущую встречу отдельно и начнёт новую. Запись звука не прервётся.` / EN `Save this meeting separately and start a new one. Audio recording will continue.` Open an accessible dialog with optional title, cancel and confirm controls; no cancellation request. Disable confirm during request. On success reset render signatures and fetch new state, retaining layout/language. On error show reason, retaining token for network retry; on 409 refresh state and ask user to confirm again rather than splitting unexpectedly.
- [ ] Verify with synthetic local server: cancellation has zero writes; empty title receives usable default; keyboard focus enters/returns from dialog; rapid double click sends one operation; failed request is visible; lost response retry keeps token; success displays new title and empty new map while old history is available. Inspect RU and EN at desktop and narrow width; no screenshot or real transcript enters Git.
- [ ] Run UI contract test, `node --check copilot/web/app.js` and full unittest discovery; commit `ui: add start new meeting with uninterrupted recording`.

### Task 5: Safe deployment and complete proof

**Files:** Modify `docs/TODO.md`; deploy only verified web-source deltas to `~/.local/share/meeting-copilot/web`.

**Interfaces:** Existing `/api/health`, `/api/state`, LaunchAgent `com.aiagentlbs.meeting-copilot`; physical Capture stays untouched.

- [ ] Run complete synthetic suite with `python3 -m unittest discover -s copilot/web -p 'test_*.py'`, Python compilation and `node --check copilot/web/app.js`. Exercise three intervals, restart, late ASR and reports end-to-end under temporary local-data roots. Check git diff for speech, screenshots, credentials and unrelated edits.
- [ ] Compare each changed source file with its installed counterpart using `diff -u`; reconcile installed-only fixes explicitly. Back up only affected installed code into a timestamped directory under local application data. Never copy config, transcripts or credentials into repository backups.
- [ ] Read bounded `/api/state` metadata: busy, audio_recording, physical ID and native PID. If AI is busy, wait for its completion without stopping native recording. Record active audio file size from metadata without opening audio. Install only reconciled web deltas, then web-only `launchctl kickstart -k gui/503/com.aiagentlbs.meeting-copilot`; do not restart Capture or manipulate audio taps.
- [ ] Verify `/api/health`, rendered split control, restored logical store, readable existing transcript by segment count only, native PID unchanged and audio growth when recording is active. Do not apply an actual split to the owner's call as a smoke test. If no active recording, report that native continuity was proved synthetically, not in a real live split.
- [ ] Update local tracker: implementation/test/deployment status and separate actionable limitation for bounded audio export, explaining whole-recording audio is intentionally omitted from split-meeting delivery. Commit docs with `docs: record logical meeting verification` and report exact tests, deployed state and remaining limitations. Do not push or publish a package as part of this change.

## Plan Self-Review

- Spec coverage: Tasks 1–3 implement persistence, routing, recovery, AI ownership and report isolation; Task 4 implements confirmation and visible feedback; Task 5 verifies installation without Capture restart.
- Interface consistency: `MeetingBoundaries.split/project/revision` and snapshot fields are defined once and consumed unchanged. Native physical ID and logical ID stay separate.
- Review Focus: all five conditions have explicit tests in their owning tasks.
- Scope: no native binary rebuild, no retrospective splitting, no new recording system, no restored AI reset, no public release or invented missing speech.
