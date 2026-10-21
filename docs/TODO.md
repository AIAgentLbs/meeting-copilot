# MeetOnTrack remaining work

Tracker: open items mirror the private `MEETONTRACK` project (migrated 2026-10-21);
each carries its `MEETONTRACK-N` number. Add and close work there first.

Audit updated 2026-10-19. Source tests, installed Mac hotfixes, candidate packages
and accepted public releases are different milestones. This file mirrors the
tracker; closed source fixes below are not proof of both-platform release.
Latest installed delivery/OAuth evidence:
[2026-10-19 acceptance](releases/2026-10-19-delivery-acceptance.md).
Public Mac/Windows 0.1.10 packages and remaining hardware gates:
[distribution acceptance](releases/2026-10-19-public-distribution.md).
2026-10-20: public 0.1.11 Mac/Windows pre-releases (per-task AI choice):
[0.1.11 distribution acceptance](releases/2026-10-20-0.1.11-distribution.md).

- [ ] MEETONTRACK-1: `scripts/check-note-ui.cjs` fails at 0.1.11 and identically at the 0.1.10
  source (`ae27f2b`): `#note-help` shows `--:--` where the test expects the
  fixture's elapsed time `02:44`. Decide whether the hint must render the call
  time before the first state poll (product fix) or the test must wait for it
  (test fix); then run it in release checks. Not run in CI today.

Scope: end-user software only. Website/domain, analytics, SEO, comparisons,
keyword/trademark research and promotion are tracked exclusively in
`AIAgentLbs/meetontrack-website`, root `SITE_TODO.md` (local sibling checkout:
`../meetontrack-website/SITE_TODO.md` from this repository root). See `AGENTS.md`.
The 2026-10-19 file migration is complete: 37 website files moved with verified
hashes, Pages removed, and the Windows installer relocated to
`scripts/windows/install.ps1` with packaging/CI references updated.

## One macOS recorder source (2026-10-20)

- [ ] MEETONTRACK-2: There are two diverged macOS recorder sources: `capture/` here (renamed
  `meetingcopilot`, ships in the Mac package, no shared Git history with Amanu)
  and `Sources/amanu` in public `AIAgentLbs/meetontrack-recorder` (tracks
  upstream `gsamat/amanu`). Reconcile into one source in
  `meetontrack-recorder` so upstream fixes merge with `git merge master`, then
  package the Mac recorder from it like Windows and remove `capture/` here.
  Needs a file-by-file diff (for example `Config.swift` 639 vs 841 lines).

## One settings store and vocabulary across Mac, Windows and web (owner rule 2026-10-20)

- [ ] MEETONTRACK-3: All components already share `~/.config/meeting-copilot/config.json`, but
  the vocabulary diverges: the Mac app writes `transcription.engine = "parakeet"`
  while `scripts/windows/install.ps1:67` and the C# recorder use
  `engine = "local"` + `local_engine = "parakeet"`; Python reads only
  `interface_language` and `live_transcription.enabled`. Define one schema
  (`docs/config.schema.json`), migrate both vocabularies to it, and make every
  writer preserve keys it does not own (verify Swift `Config.update` and C#
  `AppSettingsStore`). Settings UIs on all platforms show the same values.

## No hardcoded providers, models or modes: AI and speech-to-text (owner rule 2026-10-20)

- [x] Phase 1 (2026-10-20): Python provider layer `copilot/web/ai_providers.py`
  (Codex app-server, Claude Code initialize, Antigravity `agy models`, Ollama
  HTTP), per-purpose choice in the shared `config.json` `ai` section
  (`docs/config.schema.json`), settings panel and per-choice Check AI in Getting
  started, all five Codex call sites routed through the layer, model ids removed
  from Python/JS/HTML and the Windows launcher message. Spec:
  `docs/specs/2026-10-20-no-hardcoded-models.md`.
- [ ] MEETONTRACK-4: Release 0.1.11 with phase 1 (packaging, both platforms).
- [x] Review round 2 (2026-10-20): file boundary enforced (Claude Code
  `--restricted` + `--add-dir` per selected root, Read/Grep/Glob only, screenshot
  read from a folder holding only a copy; Codex permissions profile via
  `-c default_permissions` + `permissions.<id>.filesystem`, run from the realpath
  binary), per-invocation ticket (choice + executable identity), discovery cache
  keyed by binary and sign-in, hard deadlines and bounded buffers, structured
  needs_choice/unavailable for translation and screenshots, per-purpose Check AI.
- [x] Antigravity is listed with its models but unavailable for every purpose
  (`permission_mode: always-proceed`, read-only/no-tools not enforceable). Reopen
  when agy offers a read-only/no-tools mode and stdin input
  (`ai_providers.AntigravityAdapter`, `capture/.../Summary/AIChoice.swift`).
- [x] Shared config writers (Python `ai_providers._file_lock`/`AISettings`,
  Swift `ConfigFile.swift`): `flock` on `config.json.lock` across
  read-modify-replace, malformed file blocks saves, 0600 temp + fsync + rename.
  Cross-process test in `test_ai_providers.py` (Python writer vs native-style
  `flock` writer).
- [x] Phase 2 (2026-10-20): Swift summary and speaker naming read
  `ai.purposes.summary` / `ai.purposes.speaker_names`; no model defaults, no
  fallback order; `--model` (+ effort/speed when chosen) passed to Codex, Claude
  and Ollama; one-time migration from `summary.backend/model/openai_model/
  ollama_model` only when present in the file (provider + model, effort and speed
  left for the person).
- [ ] MEETONTRACK-5: Codex 0.153.2 (Homebrew) ignores the `:slash_tmp` deny and lets writes land
  under the temp dir when cwd is there; reads outside the roots are denied. Our
  workdir lives in `~/.cache/meeting-copilot/ai-workdir`, so not reachable today.
  Re-verify on every new Codex version with `codex sandbox -P`.
- [ ] MEETONTRACK-6: The Claude Code boundary relies on `--restricted` (Claude Code 2.1.304).
  Add a version check or a Check AI escape probe so an older CLI without it is
  reported unavailable rather than run unrestricted.
- [x] Review round 3 (2026-10-20): Setup summary cards and the legacy summary/
  naming entries in Settings > Advanced removed; Getting started is the only place
  the AI is chosen (`SettingsSchema.legacyAIKeys` stay known for the migration).
  Ollama summaries size `num_ctx` and chunks from the model's reported
  `<arch>.context_length` and refuse a prompt that does not fit; CLI install
  locations come from one list, `copilot/web/tool_locations.json`, mirrored by
  `Tooling.listedLocations` (equality test); Ollama thinking without levels is
  unavailable; the panel shows the check snapshot of the saved choice.
- [x] Review round 4 (2026-10-20): live analysis gets HEAD, status and diff stat
  of each selected repository from the app (`server.git_metadata`), since git
  cannot start inside the read-only Codex profile; the profile is not widened.
  Swift `Tooling` picks the newest `--version` with the `MEETING_COPILOT_<TOOL>`
  override first and re-picks when a candidate file changes (same rule as
  `first_run.pick_codex`). Python Ollama sends `num_ctx`, drops whole old turns
  of chat history to fit and rejects a prompt that cannot fit; models without
  `completion` or without a reported context length are unavailable. Summary
  merges are reduced in batches until they fit. Saving one purpose keeps the
  other purposes' drafts.
- [x] Review round 5 (2026-10-20): Codex isolation flags go on every call
  without repositories, resumed turns included. Claude identity (discovery,
  readiness and session keys) includes the signed-in account from
  `.claude.json` and a hash of env credentials. Ollama keeps a session's first
  prompt (the session rules) as a system message that trimming and the
  40-message cap never drop. A legacy `summary.backend: "none"` is migrated
  once to `summary.enabled: false`. The `ai` subtree is known to the Settings
  window, so it is not reported as unread.
- [ ] MEETONTRACK-7: Bring back the Anthropic and OpenAI API-key summary backends as discovered
  providers (owner decision 2026-10-20: left out of phase 2). They need an adapter
  in `copilot/web/ai_providers.py` and `capture/.../Summary/LLMBackend.swift` that
  lists models from the provider's models endpoint with the user's key, never a
  fixed model; `SummaryKeyProbe` in `Setup/SetupSelection.swift` already checks
  keys.
- [ ] MEETONTRACK-8: Ollama context sizing counts one character as at least one token
  (`LLMBackend.ollamaInputLimit`, Python `OllamaAdapter.fit`; images are not
  counted) and keeps a fixed 4096-token reply allowance.
  Use the tokenizer (or `prompt_eval_count`) if CJK transcripts get cut or long
  answers are truncated.
- [ ] MEETONTRACK-9: Check AI for `summary` and `speaker_names` probes through the Python
  adapters, not the Swift invocation in `Summary/LLMBackend.swift`; the argv
  can drift. Add a shared argv fixture both sides test against.
- [ ] MEETONTRACK-10: Phase 3 (speech-to-text): `capture/Sources/meetingcopilot/Config.swift:63`
  defaults `transcription.engine` to `"auto"` and `:76` defaults the cloud
  provider to `"assemblyai"`. `Transcription/OpenAIEngine.swift:46` refuses
  to run until `transcription.openai.model` is set (built-in model removed; owner
  decision 2026-10-20 keeps it so until phase 3 asks for the choice).
- [ ] MEETONTRACK-11: Phase 4 (Windows): `scripts/windows/install.ps1:67-68` writes a new
  `config.json` with pinned engine/backends and no lock or ACL; `:80-85` does a
  read-modify-write without `config.json.lock`; `:96-98` pins speech models.
  `scripts/windows/meeting-copilot.ps1:16-26` looks only for Codex. C#
  `AppSettingsStore` (not in this repository) must take `config.json.lock` with
  `FileStream.Lock(0,1)` (same byte as Python `msvcrt.locking`), refuse
  malformed files and restrict the file ACL to the user (the Windows equivalent of
  0600, open on the Python side too).
- [ ] MEETONTRACK-12: Same rule for speech-to-text in `capture/` (Parakeet, AssemblyAI, OpenAI
  engines and their models): engine and model are user choices, extensible to
  future engines (for example Ollama-hosted), no fixed model in code.

## Friendly-user release gate — 2026-10-19

- [x] Corrected first-install entry: installer waits for the local assistant's
  health response and opens the browser automatically; no second terminal command.
  13 installer tests and 370 Swift tests passed. Native assistant action remains
  available idle/recording/paused; clicked successfully in the installed Mac UI.
- [x] Public 0.1.10 Mac/Windows packages passed exact archive and fresh/repeat
  installation checks. Both public archives were downloaded without credentials
  and match the pinned SHA-256 values. See the distribution acceptance above.
- [ ] MEETONTRACK-13: Complete real-device two-sided audio/permissions/reconnect testing on both
  platforms and a clean Mac. The physical Windows host was offline at the final
  release check. Local Office retrieval and new-account Google onboarding remain
  distinct open requirements; do not call the technical beta a stable release.

## Meeting library follow-up

- MEETONTRACK-14: Verify the new history drawer, filesystem-opening actions and explicit summary
  editor on packaged Windows and physical mobile devices. Current browser
  acceptance uses Chromium emulated viewports on macOS, not those devices.
- MEETONTRACK-15: Add explicitly opt-in, reviewable account-wide summary preferences separately
  from one-meeting correction requests. Current correction instructions apply
  only to the selected meeting; never silently promote them to a global rule.
- MEETONTRACK-16: Migrate legacy report branding to MeetOnTrack without changing automatic report
  delivery signatures or resending previously delivered reports. Existing PDF/HTML
  exports retain their original branding until an intentional migration/rebuild.

## MeetOnTrack updates and distribution

- Deferred by owner (2026-10-19): automatic installation is not required for the
  current release. Current acceptance is a working newer-version indicator,
  release notes and a copyable platform-specific update command. No automatic
  execution or interruption of a call. See `docs/UPDATES.md`.
- MEETONTRACK-18: Future work, not a current release blocker: automatic installation of
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

- MEETONTRACK-19: Validate multilingual switching on real, consented test audio with accents,
  background noise and overlap, beyond the synthetic EN/RU/ES acceptance.
  See `docs/ASR_LANGUAGES.md`; do not promise universal code-switch accuracy.
- MEETONTRACK-20: Reconcile AI-generated call-map items when a final transcript replaces an
  erroneous live version: supersede unsupported generated items with provenance,
  preserve manual notes/status edits and retain an audit trail. Do not blindly
  delete the journal or infer that refreshing the transcript fixes old analysis.
- MEETONTRACK-21: Repair or document the local CLT 6.3.2 test-toolchain discovery failure
  (`cmath`, Testing framework and TestingInterop paths). The language acceptance
  script provides explicit process-local paths; do not change the system SDK
  or install another toolchain as part of an active-call repair.

## Existing UI accessibility warnings

- MEETONTRACK-22: Verify the existing muted-text contrast and dialog content padding in
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
- MEETONTRACK-24: Add bounded audio export for logical meeting intervals. Current history shows
  the original recording range; split-meeting external reports omit whole audio
  intentionally to prevent disclosure of adjacent meetings. Implement range
  export from original tracks, test exact bounds and report attachment isolation.

## Windows beta acceptance gaps

- MEETONTRACK-25: Keep the full Python suite platform-aware: three security tests currently
  assume POSIX mode 0600, and a recorder test assumes POSIX path spelling.
  Windows ACL checks must replace, not silently skip, the security assertions.
- MEETONTRACK-26: Optional screen OCR/active-tile detection requires Pillow and NumPy, not
  shipped in the minimal embedded Python package. Do not claim that feature
  works on Windows until dependencies and an actual UI test are included.
- MEETONTRACK-27: Add packaged-application audio and recognition-resume smoke testing to the
  release gate, in addition to native unit tests and installer fixture tests.
- MEETONTRACK-28: Verify extended real-call reconnects and report/PDF/delivery parity before
  promoting the unsigned Windows technical beta to a stable release.
- MEETONTRACK-29: Windows signed distribution and automatic-install acceptance remain future
  work; verify release notifications and manual update instructions now.
- MEETONTRACK-65: Upgrade can keep serving the previous version (found 2026-10-21 while fixing
  the macOS LaunchAgent restart race). `scripts/windows/install.ps1` never stops
  the running web server, and `meeting-copilot.ps1` reuses any healthy server on
  port 43121, so the old `versions\<old>\web\server.py` keeps running after an
  update until logoff. Its health check also accepts `ok: true` from an
  unrelated service. Proposed: stop only our own server (match the process
  command line to `MeetingCopilot\versions\*\web\server.py`), wait for the port
  to be free, start the new one, and require `service == 'meeting-copilot'`.

## Repository meeting history

Requested: after a meeting ends, identify the relevant selected GitHub/GitLab
repository and save a concise meeting history there.

Do not copy the same meeting to every active repository. The current fallback
scope means "search all selected repositories", not "publish to all". Some
meetings have no matching project alias; some projects map to multiple repos.

Acceptance criteria:

- MEETONTRACK-30: Use the meeting's explicit project/repository choice first. Automatic routing
  is allowed only for one unambiguous project and explicitly permitted private
  destination repositories. Otherwise show a pending routing choice.
- MEETONTRACK-31: Save a reviewed, project-specific brief under `docs/meetings/` with meeting ID,
  date, decisions, actions and links to the local full report. Never publish raw
  audio, screenshots, transcripts, chat, credentials or a report containing
  unrelated client details.
- Keep private deal economics out of repositories other than the allowlisted
  financial repositories. Do not infer or distribute private amounts.
- MEETONTRACK-33: Make writes idempotent by meeting ID, show per-repository status in meeting
  history, and verify the remote GitHub/GitLab revision after push. Never claim
  completion from local Git state alone.
- Owner confirmed on 2026-09-25: automatic writes are permitted only to
  verified private repositories for an unambiguous project; ambiguous meetings
  stay pending for selection. Recheck current GitHub/GitLab authentication rather
  than relying on the historical missing-credentials observation. Unattended
  publication remains off until private visibility and real push/readback pass.
- MEETONTRACK-35: Evaluate [Laya](https://github.com/NandhaKishorM/laya) as an optional local
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
- [ ] MEETONTRACK-36: Finish real new-account OAuth acceptance: use a user's own Desktop client
  to consent, check identity/scopes, refresh, send an authorized test report, upload
  to the chosen folder, search enabled sources and disconnect on clean Mac and
  Windows. Automated protocol tests and synthetic Chrome/API import do not prove
  provider consent or Windows DPAPI. Never bundle owner credentials.
- [ ] MEETONTRACK-37: Verify SMTP against an owner-approved test account and exercise native
  Keychain/Windows DPAPI credential roundtrips on both OSes. Current SMTP protocol
  and consent checks are automated; real SMTP delivery and Windows runtime are
  not established by those tests.
- [x] 2026-10-19: repaired Telegram interpreter selection and bundled hash-locked
  pure-Python Telethon dependencies for both packagers; Mac authorization checked
  without sending. Unknown outcomes no longer trigger an automatic duplicate.
- [ ] MEETONTRACK-38: Verify Telegram from both exact installed packages with explicit test-send
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

- [ ] MEETONTRACK-39: Simplify the first-run path in the native setup: explain the outcome,
  show only missing required steps, and move optional
  cloud providers, file locations and advanced choices into settings. Distinguish
  local transcription costs from optional AI-provider charges. Validate with a
  first-time user who has not received instructions from the developer.
- [ ] MEETONTRACK-40: Make live meeting assistance reachable after setup. The reviewed capture
  screen has live transcription disabled and a separate final transcription model;
  explain this distinction and make the required live path explicit. After either
  completion or "Later", open a clear status/start screen with the exact remaining
  prerequisite and a working action, rather than leaving the app undiscoverable.
- [ ] MEETONTRACK-41: Unify MeetOnTrack branding across the shipped native app, menu-bar icon,
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
- [ ] MEETONTRACK-42: Add a discoverable context-connection walkthrough: show supported sources,
  connected/searchable status and a sample grounded answer. Explain repositories,
  local documents and Google sources individually; do not imply that spreadsheet
  or document ingestion exists merely because repository search works.
- [ ] MEETONTRACK-43: Complete release acceptance for connected sources (`docs/CONTEXT_SOURCES.md`):
  folder/Drive implementation and synthetic API/LLM/handler regressions are in source;
  verify native folder selection on Windows and rendered controls in Mike's Chrome,
  then include them in the tested public package. Later Mac Chrome checks do not
  substitute for Windows selection or clean installed-package acceptance.
- [ ] MEETONTRACK-44: Extend folder retrieval beyond UTF-8 text/CSV/code to PDF and Office documents
  with bounded, read-only extractors (OfficeCLI for supported Office operations).
  Keep formats explicit in `getting-started.js`; never imply binary ingestion works
  because a directory can be connected. Add cancellation for slow network mounts
  before claiming the cooperative search time budget is a hard deadline.
- [ ] MEETONTRACK-45: Check installed models and actual provider readiness before requesting
  downloads or reporting "ready". An executable/version response alone does not
  prove successful authenticated inference or available quota. Show download size,
  disk use and reusable-model compatibility; offer a short functional check.
- [ ] MEETONTRACK-46: Expose AI authentication, quota and provider failures in the main assistant
  with a recovery action, while keeping capture state independent. Test missing
  subscription, expired authentication, exhausted quota and network failures;
  preserve queued work and prevent a silently empty assistant.
- [ ] MEETONTRACK-47: Add packaged recording-state regression tests for repeated Start clicks,
  actual audio progress, prolonged silence and end-of-call detection. Feedback
  describes an older upstream recording-silence incident, not a verified failure
  of this build. Require idempotent Start, visible failure/health feedback, bounded
  resource growth and recovery without discarding valid quiet meeting intervals.
- [ ] MEETONTRACK-48: Test packaged Mac and Windows capture with wired/Bluetooth headphones,
  reconnects, and input/output device switching during a call. Verify both local
  and remote audio tracks plus transcription continuity; one successful personal
  call is not evidence for every supported device transition.
- [ ] MEETONTRACK-49: Verify the end-user installer and documented first-run path from launch
  through context selection, recording and a useful answer. Evaluate a direct
  downloadable installer after packaging/signing acceptance. Website placement
  and promotional demos belong to the website backlog, not this release gate.

## AI provider layer: Codex review round 5 leftovers (2026-10-20, P2)

- [ ] MEETONTRACK-50: Ollama live chat pins the whole first prompt (transcript, question,
  excerpts) as the system message, so trimming cannot reclaim it and valid
  continuations are rejected on small contexts (`copilot/web/ai_providers.py`
  ~603). Split immutable session rules from meeting content; let old
  snapshots be trimmed.
- [ ] MEETONTRACK-51: `live_translation.py` ~84: a status change to `needs_choice` /
  `unavailable` does not bump `revision`, so `AnnotationCache.snapshot()`
  keeps serving the old empty `translation_state`. Bump revision on status
  change.
- [ ] MEETONTRACK-52: `live_translation.py` ~77: an English/Russian/undetected segment clears
  `needs_choice` while foreign segments still wait for a translation choice.
  Keep the status while unresolved jobs need a choice.

## Live translation: no-op "EN:" lines on Russian speech (found 2026-10-21)

- [ ] MEETONTRACK-64: Short Russian phrases are misdetected by `detect-speech-language` as
  `bg`/`kk` with confidence 1.0, so `live_translation.py` `_work` sends them for
  translation; the prompt says "keep Russian words as Russian", the model returns
  the Russian text unchanged, and the segment gets `translation_en` equal to its
  own text. The UI and the report (`archive.py` ~1751) then show a duplicate
  "EN:" line. Seen on meeting 51FE8DC8 (2026-10-20): 4 such segments. Proposed:
  store no translation when the result equals the source text (case/space
  normalized), and consider skipping Cyrillic-only text detected as bg/kk/uk
  when the meeting language is Russian. Since 2026-10-21 `sync_transcript` keeps
  archived translations across restarts, so previously stored no-op lines stay
  until the text changes or a cleanup pass drops them.
