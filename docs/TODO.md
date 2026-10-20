# MeetOnTrack remaining work

Audit updated 2026-10-19. Source tests, installed Mac hotfixes, candidate packages
and accepted public releases are different milestones. This file is the complete
local backlog; closed source fixes below are not proof of both-platform release.
Latest installed delivery/OAuth evidence:
[2026-10-19 acceptance](releases/2026-10-19-delivery-acceptance.md).
Public Mac/Windows 0.1.10 packages and remaining hardware gates:
[distribution acceptance](releases/2026-10-19-public-distribution.md).

Scope: end-user software only. Website/domain, analytics, SEO, comparisons,
keyword/trademark research and promotion are tracked exclusively in
`AIAgentLbs/meeting-copilot`, root `SITE_TODO.md` (local sibling checkout:
`../meeting-copilot/SITE_TODO.md` from this repository root). See `AGENTS.md`.
The 2026-10-19 file migration is complete: 37 website files moved with verified
hashes, Pages removed, and the Windows installer relocated to
`scripts/windows/install.ps1` with packaging/CI references updated.

## AI provider, model, effort and fast-mode selection (owner request 2026-10-20)

- [ ] Replace the hardcoded `gpt-6.1-sol` (`copilot/web/first_run.py:84`,
  `server.py:2024`, `live_translation.py:62`, `summary_rewrite.py:9`) with a user
  choice: provider (Codex, Claude Code, Gemini via `agy`) shown only when its CLI
  is installed and signed in; model list read from that CLI, not hardcoded;
  effort levels the chosen model supports; fast-mode toggle only where the model
  and the user's plan support it. Separate settings for live in-call analysis
  (fast mode useful) and post-call summaries. Check AI tests the exact chosen
  combination and names the reason on refusal (old CLI does not know the model,
  plan excludes the model, not signed in). Why: an older Codex works with models
  it knows; today the app fails with any CLI that does not know `gpt-6.1-sol`.
  Before building, verify each CLI's model/effort/fast flags and plan
  availability from current vendor docs (do not rely on memory).

## Friendly-user release gate — 2026-10-19

- [x] Corrected first-install entry: installer waits for the local assistant's
  health response and opens the browser automatically; no second terminal command.
  13 installer tests and 370 Swift tests passed. Native assistant action remains
  available idle/recording/paused; clicked successfully in the installed Mac UI.
- [x] Public 0.1.10 Mac/Windows packages passed exact archive and fresh/repeat
  installation checks. Both public archives were downloaded without credentials
  and match the pinned SHA-256 values. See the distribution acceptance above.
- [ ] Complete real-device two-sided audio/permissions/reconnect testing on both
  platforms and a clean Mac. The physical Windows host was offline at the final
  release check. Local Office retrieval and new-account Google onboarding remain
  distinct open requirements; do not call the technical beta a stable release.

## Meeting library follow-up

- Verify the new history drawer, filesystem-opening actions and explicit summary
  editor on packaged Windows and physical mobile devices. Current browser
  acceptance uses Chromium emulated viewports on macOS, not those devices.
- Add explicitly opt-in, reviewable account-wide summary preferences separately
  from one-meeting correction requests. Current correction instructions apply
  only to the selected meeting; never silently promote them to a global rule.
- Migrate legacy report branding to MeetOnTrack without changing automatic report
  delivery signatures or resending previously delivered reports. Existing PDF/HTML
  exports retain their original branding until an intentional migration/rebuild.

## MeetOnTrack updates and distribution

- Deferred by owner (2026-10-19): automatic installation is not required for the
  current release. Current acceptance is a working newer-version indicator,
  release notes and a copyable platform-specific update command. No automatic
  execution or interruption of a call. See `docs/UPDATES.md`.
- Future work, not a current release blocker: automatic installation of
  the complete Capture + web + Python product, not just release notifications.
  Migrate Mac's split payload into the Sparkle update unit and Windows ZIP installs
  into the owned Velopack channel; retain recordings/settings and provide rollback.
  Validate exact N-to-N+1 packages, busy-call deferral and interrupted updates on
  both OSes before changing the public website promise. See `docs/UPDATES.md`.
  Current gaps: complete-product updater packaging/signature verification and
  cross-version acceptance are unfinished; Windows SSH returned no host key
  despite Tailscale online. No valid Mac Developer ID identity was found, but
  Apple enrollment is not a prerequisite for Ed25519-signed update archives.
- [x] 0.1.10 public Mac archive contains release identity and embedded runtime;
  anonymous downloaded bytes passed exact manifest/fresh/repeat acceptance.
- [x] Published Mac/Windows packages contain the M icon and release checker.
  Both platform/channel choices recognize the actual public 0.1.10 release feed.
  Existing old installs without the checker require one manual update first.
  Signing/appcast validation belongs to deferred automatic-installer work.

## Multilingual recognition acceptance

- Validate multilingual switching on real, consented test audio with accents,
  background noise and overlap, beyond the synthetic EN/RU/ES acceptance.
  See `docs/ASR_LANGUAGES.md`; do not promise universal code-switch accuracy.
- Reconcile AI-generated call-map items when a final transcript replaces an
  erroneous live version: supersede unsupported generated items with provenance,
  preserve manual notes/status edits and retain an audit trail. Do not blindly
  delete the journal or infer that refreshing the transcript fixes old analysis.
- Repair or document the local CLT 6.3.2 test-toolchain discovery failure
  (`cmath`, Testing framework and TestingInterop paths). The language acceptance
  script provides explicit process-local paths; do not change the system SDK
  or install another toolchain as part of an active-call repair.

## Existing UI accessibility warnings

- Verify the existing muted-text contrast and dialog content padding in
  `copilot/web/styles.css` with actual light/dark UI screenshots and computed
  styles. The Impeccable scan during removal of AI chat reset flagged these
  unrelated areas; they were not changed in that scoped task. Adjust verified
  failures without altering the recording or meeting-context workflows.
  The 2026-10-19 bounded detector pass also flagged 10px company/language controls
  and small functional labels. Include these in the same accessibility acceptance.

## Continuous recording meeting boundaries

- Completed and installed on Mac 2026-10-13: Start new meeting from now without
  restarting Capture. Persist independent logical meeting intervals over the
  original audio; isolate transcript, AI jobs/context, journal, screenshots,
  chat, reports and history. Prevent archive continuous-chain merging across
  explicit boundaries and keep recovery targeting the physical recording ID.
  Reviewed implementation and synthetic restart/routing tests:
  [2026-10-13 continuous meeting boundary specification](superpowers/specs/2026-10-13-continuous-meeting-boundary-design.md).
  [Implementation plan](superpowers/plans/2026-10-13-continuous-meeting-boundary.md).
  161 Python tests and browser cancellation/retry/conflict/history checks pass.
  Capture was not restarted. No actual boundary was applied to the owner's call.
- Add bounded audio export for logical meeting intervals. Current history shows
  the original recording range; split-meeting external reports omit whole audio
  intentionally to prevent disclosure of adjacent meetings. Implement range
  export from original tracks, test exact bounds and report attachment isolation.

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
- Windows signed distribution and automatic-install acceptance remain future
  work; verify release notifications and manual update instructions now.

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
  stay pending for selection. Recheck current GitHub/GitLab authentication rather
  than relying on the historical missing-credentials observation. Unattended
  publication remains off until private visibility and real push/readback pass.
- Evaluate [Laya](https://github.com/NandhaKishorM/laya) as an optional local
  candidate scorer for one or more repos. It must not independently authorize
  publication: validate on labelled meeting-to-repo examples, calibrate the
  multilingual model, then apply the private-repo and ambiguity gates above.

## Google delivery

- [x] 2026-10-19: diagnosed the rejected attachment outside the Google CLI cwd;
  fixed attachment/upload subprocess cwd, installed the fix on Mac, and verified
  the owner-authorized resend through Gmail Sent and Inbox. Safe reason codes,
  durable delivery receipts and explicit per-channel retry controls are added.
  Do not backfill other historical reports without duplicate checks and approval.

- [x] 2026-10-19: added delivery settings, independent channel consent, named
  Google profile selection/connect/disconnect/check, SMTP/TLS, recipient and
  Drive folder controls. SMTP draft checks do not save consent or routing;
  account checks retain drafts. Local reports work without integrations. See
  [DELIVERY.md](DELIVERY.md) for tests and exact acceptance boundaries.

- [x] 2026-10-19 source implementation: import the user's Desktop OAuth JSON in
  Settings; protected OS store, native PKCE/loopback login, expected-account check,
  refresh, disconnect, Gmail/Drive delivery and read-only context adapters.
  No shared product Cloud project, external connector or profile registry required.
  Import/connect do not opt in to delivery or context search. See DELIVERY.md.
  Installed and read back on Mac; native Keychain JSON roundtrip passed with a
  disposable item. Settings reads no longer wait behind the archive delivery
  lock; edits return an actionable busy response. Concurrency regressions added.
- [ ] Finish real new-account OAuth acceptance: use a user's own Desktop client
  to consent, check identity/scopes, refresh, send an authorized test report, upload
  to the chosen folder, search enabled sources and disconnect on clean Mac and
  Windows. Automated protocol tests and synthetic Chrome/API import do not prove
  provider consent or Windows DPAPI. Never bundle owner credentials.
- [ ] Verify SMTP against an owner-approved test account and exercise native
  Keychain/Windows DPAPI credential roundtrips on both OSes. Current SMTP protocol
  and consent checks are automated; real SMTP delivery and Windows runtime are
  not established by those tests.
- [x] 2026-10-19: repaired Telegram interpreter selection and bundled hash-locked
  pure-Python Telethon dependencies for both packagers; Mac authorization checked
  without sending. Unknown outcomes no longer trigger an automatic duplicate.
- [ ] Verify Telegram from both exact installed packages with explicit test-send
  authorization, including Windows dependency loading. Do not silently use another
  account/session or mark an unacknowledged report as sent.

The application retries unsent reports and shows recent failures in the UI.
Gmail/Drive use either the selected native own-client OAuth connection or a named,
identity-checked legacy wrapper; missing `gog` authorization is not a failure.
A completed report from 2026-09-25
was uploaded and delivered through this path, including Telegram and Drive
links. Automatic retries are limited to the most recent three days; older
pending reports need a duplicate check against Sent mail before any backfill.

## First-run acceptance gaps (feedback reviewed 2026-10-16)

These are product requirements derived from installation feedback and screenshots,
not reproduced runtime failures. Private chat messages and screenshots are not
stored in this repository. Verify the public installed package as well as source.

- [ ] Simplify the first-run path in the native setup: explain the outcome,
  show only missing required steps, and move optional
  cloud providers, file locations and advanced choices into settings. Distinguish
  local transcription costs from optional AI-provider charges. Validate with a
  first-time user who has not received instructions from the developer.
- [ ] Make live meeting assistance reachable after setup. The reviewed capture
  screen has live transcription disabled and a separate final transcription model;
  explain this distinction and make the required live path explicit. After either
  completion or "Later", open a clear status/start screen with the exact remaining
  prerequisite and a working action, rather than leaving the app undiscoverable.
- [ ] Unify MeetOnTrack branding across the shipped native app, menu-bar icon,
  language picker, menu actions, settings and web assistant. Review all installed
  entry points. On 2026-10-19 Swift UI/branding tests and Windows UI source use
  MeetOnTrack; the installed Mac display name was verified. Old upstream names
  remain only in compatibility identifiers/paths and mandatory attribution, not
  product labels. Windows installed UI/icon acceptance is still unverified.
  Use plain location labels such as "top menu bar on your Mac" and expose a clear
  action to open the assistant, including when the menu bar is crowded.
  2026-10-19: M-and-dot icon built and installed on Mac; owner confirmed Dock
  and menu-bar icons changed. Mac bundle and native views share one renderer;
  legacy icon entry point delegates to it. Windows generator changed in the
  native capture repository, but real Windows build/tray/taskbar acceptance and
  both updated public packages are distributed as 0.1.10. Real Windows
  tray/taskbar acceptance is still open; hosted native/package checks passed.
- [ ] Add a discoverable context-connection walkthrough: show supported sources,
  connected/searchable status and a sample grounded answer. Explain repositories,
  local documents and Google sources individually; do not imply that spreadsheet
  or document ingestion exists merely because repository search works.
- [ ] Complete release acceptance for connected sources (`docs/CONTEXT_SOURCES.md`):
  folder/Drive implementation and synthetic API/LLM/handler regressions are in source;
  verify native folder selection on Windows and rendered controls in Mike's Chrome,
  then include them in the tested public package. Later Mac Chrome checks do not
  substitute for Windows selection or clean installed-package acceptance.
- [ ] Extend folder retrieval beyond UTF-8 text/CSV/code to PDF and Office documents
  with bounded, read-only extractors (OfficeCLI for supported Office operations).
  Keep formats explicit in `getting-started.js`; never imply binary ingestion works
  because a directory can be connected. Add cancellation for slow network mounts
  before claiming the cooperative search time budget is a hard deadline.
- [ ] Check installed models and actual provider readiness before requesting
  downloads or reporting "ready". An executable/version response alone does not
  prove successful authenticated inference or available quota. Show download size,
  disk use and reusable-model compatibility; offer a short functional check.
- [ ] Expose AI authentication, quota and provider failures in the main assistant
  with a recovery action, while keeping capture state independent. Test missing
  subscription, expired authentication, exhausted quota and network failures;
  preserve queued work and prevent a silently empty assistant.
- [ ] Add packaged recording-state regression tests for repeated Start clicks,
  actual audio progress, prolonged silence and end-of-call detection. Feedback
  describes an older upstream recording-silence incident, not a verified failure
  of this build. Require idempotent Start, visible failure/health feedback, bounded
  resource growth and recovery without discarding valid quiet meeting intervals.
- [ ] Test packaged Mac and Windows capture with wired/Bluetooth headphones,
  reconnects, and input/output device switching during a call. Verify both local
  and remote audio tracks plus transcription continuity; one successful personal
  call is not evidence for every supported device transition.
- [ ] Verify the end-user installer and documented first-run path from launch
  through context selection, recording and a useful answer. Evaluate a direct
  downloadable installer after packaging/signing acceptance. Website placement
  and promotional demos belong to the website backlog, not this release gate.
