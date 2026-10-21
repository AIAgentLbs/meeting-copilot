# No hardcoded AI or speech providers, models or modes

Owner rule 2026-10-20 (see `AGENTS.md`). Status: phase 1 implemented 2026-10-20
(Python layer `copilot/web/ai_providers.py`), review fixes and phase 2 (Swift
summary and speaker naming) implemented 2026-10-20; phases 3-4 planned. Backlog:
`docs/TODO.md`.

## Single AI choice (owner decision 2026-10-21, supersedes per-purpose selection)

"I want to choose Codex once and be done." The person chooses the AI once and
every task uses it; the reference UX is FluidVoice's single AI provider/model
setting. Where the sections below say "per purpose", read "one choice, checked
per task".

- Settings: `ai.choice` `{provider, model, effort, speed}` in the shared
  `config.json`, same completeness rules as before (all four keys; `effort` /
  `speed` are `""` when discovery offers none; a missing key is needs_choice,
  never a default). Python writes it (`AISettings.set_choice`, the locked
  writer); Swift only reads it.
- Every task resolves to it: Python `AIService.resolve(task)`, Swift
  `AIChoice.resolve(in:)` / `LLMBackend.resolve()`. Task capability needs stay
  per task: screenshots need a model discovery reports as accepting images; live
  analysis with selected repositories needs file access (Codex, Claude Code).
  A task the choice cannot do is unavailable with the reason ("your chosen model
  does not accept images, so screenshots are not analysed"); no other task is
  blocked and nothing falls back to another model.
- Migration, once (`ai_providers.migrated_choice`): when `ai.choice` is absent,
  the complete `ai.purposes` choices are adopted if they are all identical or
  only one exists; if several differ, `ai.purposes.live_analysis` if complete,
  else none (needs_choice). Without complete ones, the legacy
  `summary.backend` / `speaker_names.backend` (phase-2 mapping) feed the choice
  by the same rule, as a partial choice that still needs effort and speed.
  Python writes the result; `ai.purposes` is then never read and stays in the
  file untouched. Until Python has written it, Swift derives the same complete
  choice in memory (`AIChoice.stored`); the shared cases are
  `copilot/web/fixture_ai_choice_migration.json`. Swift no longer writes `ai`;
  its `migrateLegacy` only turns `summary.backend: "none"` into
  `summary.enabled: false`.
- API for the Getting started UI: `GET /api/ai` returns `providers`, `choice`
  (state, choice, reason), `purposes` (state and reason per task with the
  choice) and `check` (last Check AI result per task); `GET /api/ai/options`
  is discovery per provider; `POST /api/ai/choice {choice}` saves;
  `POST /api/getting-started/check-ai` runs Check AI.
- Check AI runs each task's probe against the one choice; tasks with the same
  probe kind (text, image, files) share one request. A task the choice cannot do
  is listed unavailable and not probed; overall state `partial` means the choice
  works and only such tasks are unavailable.

## Problem (audit 2026-10-20)

- Python web assistant: five separate Codex subprocess call sites, four pin
  `gpt-6.1-sol` (`server.py:2024`, `first_run.py:84`, `live_translation.py:62`,
  `summary_rewrite.py:9`), one passes no model (`frame_relevance.py:29`). All use
  `--ignore-user-config`; no effort or speed is ever set; UI text names the model.
- Swift summary/speaker naming (`Summary/LLMBackend.swift`) has settings but
  code defaults (`gpt-5`, `claude-opus-5`, `qwen3:8b`), a fixed fallback order,
  and never passes `--model` to Claude CLI. Python ignores these settings.
- STT: final engine is configurable, but live STT (Nemotron), diarization
  (`LSEEND .dihard3`), `transcribe-audio` (always Parakeet) and the network
  fallback to Parakeet are fixed; cloud engine set is closed. Windows installer
  writes `parakeet` and downloads two pinned `.gguf` models; Windows launcher
  looks only for Codex and prints the model.

## Discovery: where options come from (verified 2026-10-20)

Options are read from the exact binary or service the app will call.

- Codex: `codex app-server` JSON-RPC. `model/list` (paged) gives per model
  `supportedReasoningEfforts`, `defaultReasoningEffort`, `serviceTiers`
  (fast = tier `priority`, named "Fast"); `account/read` gives auth type and
  `planType`; `config/read` gives the user's current choice. Present in 0.144,
  0.153 and 0.159; the list differs by client version (0.153 has no
  `gpt-6.1-sol`), so always query the binary that will run. Apply with
  `-m`, `-c model_reasoning_effort=...`, `-c service_tier=...`.
  Docs: https://developers.openai.com/codex/speed ("Fast mode is available in
  the ChatGPT desktop app, Codex CLI, and IDE extension when you sign in with
  ChatGPT"; 2.5x subscription usage).
- Claude Code: `claude -p --input-format stream-json --output-format
  stream-json --verbose`, control request `initialize` (no inference) gives
  `models[]` with `supportedEffortLevels`, `supportsFastMode`, account
  `subscriptionType`, and `fast_mode_state` / `fast_mode_disabled_reason`.
  Apply with `--model`, `--effort`, `--settings '{"fastMode":true}'`.
  Fast mode needs usage credits on subscription plans
  (https://code.claude.com/docs/en/fast-mode). `claude auth status --json`
  for sign-in.
- Gemini: Antigravity `agy models` (tab-separated `id<TAB>name`; effort is
  the id suffix; list is filtered by account). No fast mode, no plan info,
  no JSON. Legacy `gemini` CLI is refused for personal Google logins.
- Ollama: `GET /api/tags` for models; `POST /api/show` `thinking.values` /
  `default` for levels (`[false]` = no thinking; omitted = no metadata).
  https://docs.ollama.com/capabilities/thinking
- STT discovery per engine: to be researched before phase 3 (FluidAudio
  model variants, AssemblyAI speech models, OpenAI transcription models).

## Design

- One provider layer per runtime with adapters (Codex, Claude Code, Antigravity,
  Ollama; extensible). Adapters know how to discover and how to call; they hold
  no model ids.
- Selection is per purpose: live analysis and chat, live translation, frame
  relevance, summary rewrite, summary, speaker names. Each purpose stores
  provider, model, effort, speed. Live purposes may use fast mode.
- Settings source: one shared file for every component,
  `~/.config/meeting-copilot/config.json` (owner decision 2026-10-20; no second
  settings file). The AI choice lives under the top-level `ai` section:
  `{"ai": {"purposes": {"live_analysis": {"provider", "model", "effort", "speed"}, ...}}}`.
  Schema: [`docs/config.schema.json`](../config.schema.json).
- Ownership: each component writes only its own sections. The Python web server
  owns `ai` (Swift reads `ai.purposes.summary` and `ai.purposes.speaker_names`
  and may write them once, for the migration below); Swift (`Config`) and the
  Windows installer / C# recorder (`AppSettingsStore`, same path) own the
  capture sections.
- Migration (Swift, once, `Summary/AIChoice.swift` `migrateLegacy`): when
  `ai.purposes.summary` or `ai.purposes.speaker_names` is absent and the file
  itself names a legacy backend (`claude-cli`, `codex-cli`, `ollama` in
  `summary.backend` / `speaker_names.backend`), write `{provider[, model]}` from
  the keys present in the file (`summary.model`, `openai_model`, `ollama_model`,
  `speaker_names.model`). Never from code defaults. Effort and speed are left
  out, so the partial choice reports needs_choice everywhere until the person
  finishes it in Getting started.
- Write protocol, every writer, every OS:
  1. take the advisory lock on `config.json.lock` (same folder, created 0600) and
     hold it across the whole read-modify-replace;
  2. read: missing file = empty object (saving allowed); valid JSON object =
     use it; unreadable, malformed or not an object = refuse to save and show the
     error (never treat it as empty);
  3. change only the owned keys, keep every other key;
  4. write a temp file in the same folder, private before any byte is written
     (0600), flush and fsync, then rename it over `config.json`;
  5. release the lock (closing the lock file releases it).
  macOS/Linux: `flock(LOCK_EX)` (Python `fcntl.flock`, Swift `flock`). Windows:
  `msvcrt.locking(LK_LOCK)` on byte 0 of the lock file (Python; retries about
  10 s, then fails the save); the PowerShell installer and the C# recorder must
  lock the same byte (`FileStream.Lock(0, 1)`) and set an owner-only ACL instead
  of 0600 (phase 4, `docs/TODO.md`).
- Purposes: `live_analysis` (analysis, chat and the context planners),
  `live_translation`, `frame_relevance`, `summary_rewrite` (Python), `summary`,
  `speaker_names` (Swift; listed, saved and checked by Python).
- A choice is complete only with all four keys. `effort` is one of the levels
  discovery lists, or `""` when it lists none. `speed` is `"standard"` (default
  tier, chosen explicitly), a tier id discovery lists, or `""` when no tier is
  offered. A missing key means not chosen (`needs_choice`); the UI never
  preselects a value. A model whose discovery entry lacks a capability we must
  choose from (effort list) is shown unavailable with the reason.
- Purpose capabilities: screenshots need a model that discovery reports as
  accepting images (Codex `inputModalities`, Ollama `capabilities: vision`;
  Claude Code does not report it, so it is not offered there). Live analysis
  with selected repositories needs file access: Codex and Claude Code only;
  Ollama refuses with a reason.
- No silent default: if a purpose has no valid choice, the UI asks. A stored
  choice the installed provider no longer offers is shown as unavailable with
  the reason (old CLI, plan, not signed in).
- Check AI tests each purpose separately with a purpose-appropriate probe: text
  for translation and summaries, a generated image for screenshots, a temporary
  file inside a temporary root for live analysis. A result belongs to the exact
  choice and executable it tested; any change shows the purpose as unchecked.
- STT: an engine registry for final, live, retranscription and diarization,
  engine and model chosen by the user, options discovered from the engine.

## Phases

1. Python AI provider layer + discovery + per-purpose selection UI + Check AI;
   remove all model ids from Python, JS and UI text. Release 0.1.11. Done
   2026-10-20 except the release itself. Per-purpose selection superseded by
   the single choice (owner decision 2026-10-21, section above).
2. Swift summary/naming read `ai.purposes.summary` and `ai.purposes.speaker_names`
   from `config.json`; remove code defaults and the fixed order; pass the model,
   effort and speed to every CLI. Done 2026-10-20. Superseded 2026-10-21: Swift
   reads `ai.choice` (section above).
3. STT engine registry on Mac (live, final, retranscription, diarization).
4. Windows: launcher, installer and the C# recorder follow the same rule.

## Phase 1 implementation notes (2026-10-20)

- Discovery is lazy and cached per provider (5 min when available, 30 s when
  not; "Refresh lists" forces it), with a timeout per call; failures become
  `unavailable: <reason>`. Nothing runs at import or server start.
- Every invocation runs from a snapshot (`AIService.resolve` -> ticket: choice,
  state, executable, key). One question uses one ticket for all its calls; a
  provider session (Codex thread, Claude session, Ollama history kept in memory)
  is resumed only by the ticket key that opened it. The key covers the choice and
  the executable identity (resolved path, mtime, size; Codex also `auth.json`).
- Discovery is bound to that identity: a changed binary or sign-in re-runs it,
  and the call uses the executable discovery ran. Discovery loops have one
  absolute deadline, bounded line and total output buffers, and Ollama model
  probes share one budget with per-model failures isolated.
- Model recorded: Claude reports the model that ran (stream `init`); Codex
  `exec --json` and Ollama report nothing beyond the request, so the requested
  id is recorded.
- File boundary (review fix A2): every call starts in one empty working
  directory. Codex: no `--sandbox` flag; a permissions profile passed with `-c`
  (`default_permissions="meetontrack"`, `permissions.meetontrack.filesystem`)
  makes only `:minimal`, the working directory, Codex's own package and the
  selected repositories readable, and every entry read-only (verified with
  `codex sandbox` on 0.159.2 and 0.153.2: home and other folders denied, writes
  denied outside the temp directory, network denied; 0.153.2 still allows writes
  under the temp directory). Shell and other tools are disabled when no
  repositories are given. Claude Code: `--restricted` (file tools confined to the
  working directories), `--add-dir` for each repository, only `Read,Grep,Glob`,
  `--setting-sources ""`, `--strict-mcp-config`. Screenshots: Codex gets the one
  image through `--image`; Claude reads a copy in a fresh folder that holds only
  that copy. The session rules (`SESSION.md`) travel inside the prompt, so no
  call needs `~/.config`.
- Antigravity: listed with its models but unavailable for every purpose
  ("cannot enforce read-only/no-tools: permission_mode always-proceed") until agy
  can enforce it.
- Translation and screenshots surface `needs_choice` / `unavailable` with the
  reason (`AIChoiceError`); a screenshot is not taken without a usable choice,
  so nothing is discarded as irrelevant for a missing setting.
