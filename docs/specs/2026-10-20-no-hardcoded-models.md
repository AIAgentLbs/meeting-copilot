# No hardcoded AI or speech providers, models or modes

Owner rule 2026-10-20 (see `AGENTS.md`). Status: phase 1 implemented 2026-10-20
(Python layer `copilot/web/ai_providers.py`), review fixes and phase 2 (Swift
summary and speaker naming) implemented 2026-10-20; phase 3 (one speech
recognition choice on the Mac, owner decision 2026-10-21) implemented on branch
`feat/stt-user-choice`; phase 4 planned. Backlog: `docs/TODO.md`.

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
- STT discovery per engine: see "Phase 3" below.

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
- STT: one speech recognition choice (engine, model, language, speaker model)
  used for live and final transcripts; see "Phase 3" below.

## Phases

1. Python AI provider layer + discovery + per-purpose selection UI + Check AI;
   remove all model ids from Python, JS and UI text. Release 0.1.11. Done
   2026-10-20 except the release itself. Per-purpose selection superseded by
   the single choice (owner decision 2026-10-21, section above).
2. Swift summary/naming read `ai.purposes.summary` and `ai.purposes.speaker_names`
   from `config.json`; remove code defaults and the fixed order; pass the model,
   effort and speed to every CLI. Done 2026-10-20. Superseded 2026-10-21: Swift
   reads `ai.choice` (section above).
3. One speech recognition choice on the Mac (live, final, re-transcription,
   speakers), options discovered from the engine. Done 2026-10-21 on
   `feat/stt-user-choice` (not merged).
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

## Phase 3: one speech recognition choice (owner decision 2026-10-21)

Owner: "one model for speech-to-text (it usually covers language and speaker
detection too) and a second model for analysis, like FluidVoice". FluidVoice
(GPLv3) is a behavioural reference only; none of its code is used (this
repository is MIT).

### The setting

`stt.choice` in `config.json`, owner: Python web server (Getting started card);
the Swift app reads it and writes it only for the one-time migration below.

    {"stt": {"choice": {"engine": "...", "model": "...", "language": "..."}}}

- All three keys are required. A missing key, or an empty `engine`, `model` or
  `language`, means not chosen (`needs_choice`). Nothing is ever filled in by
  code and the UI preselects nothing.
- `engine`: `fluidaudio` (local, Apple Silicon only), `assemblyai`, `openai`.
- `model`: an id exactly as the engine's discovery lists it (free text for an
  engine whose discovery has no list, see `model_entry`).
- `language`: `auto` only when the model reports `auto_detect`; otherwise one
  of the model's `languages` (free text when `language_entry` is `free_text`).
- There is no speaker setting (owner decision 2026-10-21, see "Live and
  speakers").
- One model serves live and final transcripts. There is no fallback model and
  no per-purpose choice: a failure defers the session with its reason, and the
  person may pick another model.
- Kept as they were: `transcription.enabled` (transcribe automatically),
  `live_transcription.enabled` (live transcript on/off), API key locations.
  Read only by the migration: `transcription.engine`, `.cloud`, `.model`,
  `.language`, `.openai.model`, `.assemblyai.speech_model`.

Migration (Swift `STTChoice.migrateLegacy`, runs while `stt.choice` is absent,
writes only from keys present in the file, never from a former code default):
`transcription.engine` `parakeet` -> `{engine: fluidaudio}` plus `model` = the
FluidAudio repository name when `transcription.model` is `v3` or `v2`;
`openai` -> `{engine: openai}` plus `model` from `transcription.openai.model`;
`assemblyai` -> `{engine: assemblyai}` plus `model` from
`transcription.assemblyai.speech_model`; `auto` or absent -> nothing.
`language` is copied from a non-empty `transcription.language`, otherwise it is
the language the chosen local model implies (below).

The installer's model (owner decision 2026-10-21): a speech model the installer
downloaded is the person's own install-time choice, not a code default. When
`stt.choice` is absent (or the legacy engine was `auto`) and exactly one local
model is in our models folder (`LocalSTTModel.installed`: downloaded Parakeet
versions and Nemotron ships), the migration writes
`{engine: fluidaudio, model: <it>, language: <implied>}` with no prompt.
The implied language is `auto` when the model detects languages, its one
language when it lists one, and unknown otherwise; an unknown language adopts
nothing. Parakeet's languages come from the cached model card and Nemotron's
from the ship's own prompt dictionary, so adoption works offline; when the
card is not cached yet, the first `stt-options` run (it reads the card)
completes the adoption, and the app runs it once at start for that case. Zero
or several candidates keep `needs_choice`; a model the installer did not
download is never picked, and a stored choice is never replaced. The web card
saves the same implied language itself, so a person who picks such a model
makes no further choice.

### Discovery contract `meetontrack.stt-options/1`

`meetingcopilot stt-options --json [--refresh]` prints one JSON object. The
Windows recorder implements the same contract in phase 4. Python caches it
(5 min when it succeeded, 30 s when not) and adds `best_for` tags derived only
from the facts below (`live`, `multilingual`, `offline`, `speakers`,
`lowest_latency`).

    {
      "contract": "meetontrack.stt-options/1",
      "generated_at": "ISO 8601",
      "platform": {"os": "macos", "arch": "arm64|x86_64", "local_models": true},
      "choice": {"stored": {...} | null, "state": "ready|needs_choice|unavailable", "reason": ""},
      "engines": [{
        "id": "fluidaudio", "label": "...", "kind": "local|cloud",
        "available": true, "reason": "",
        "needs_key": false, "has_key": null | true | false,
        "model_entry": "list|free_text",
        "listing": {"source": "...", "error": ""},
        "models": [{
          "id": "...", "label": "...", "family": "...",
          "final": true | false | null,
          "live": "streaming|sliding_window|", "live_latency_ms": 1120 | null, "live_reason": "",
          "languages": ["en", ...], "language_entry": "list|free_text", "auto_detect": true | false | null,
          "speakers": true | false | null,
          "size_bytes": 123 | null, "size_is_estimate": false,
          "downloaded": true | false | null, "on_disk_bytes": 123 | null,
          "download_bytes": 123 | 0 | null,
          "found_elsewhere": [{"path": "/Users/.../FluidAudio/Models/parakeet-tdt-0.6b-v3-coreml", "bytes": 123}],
          "available": true, "reason": "",
          "source_url": "https://...",
          "benchmarks": [{"language": "en", "metric": "WER", "value": 8.9, "test_set": "FLEURS en_us"}]
        }],
        "model_template": {...}
      }]
    }

`model_template` appears only when `model_entry` is `free_text`: the facts
(same keys as a model, `id` empty) that hold for any id the person types.

`null` means unknown (for example OpenAI does not say which of its models
transcribe or diarize until a check runs); the UI shows it as unknown, never as
yes or no. Sources:

- `fluidaudio`: the model families this app has adapters for, enumerated from
  FluidAudio itself. Parakeet TDT batch models: every `AsrModelVersion` the
  adapter maps (enum cases, ids are FluidAudio's `Repo.name`), final + live by
  FluidAudio's sliding window. Nemotron multilingual streaming: one model per
  entry of the Hugging Face `manifest.json` `ships[]` (id
  `<Repo.name>/<ship path>`), live streaming at the ship's `chunk_ms`, final by
  feeding the file through the same streaming decoder with token timings.
  Languages: Parakeet from the Hugging Face model card `language` list;
  Nemotron from the ship's `metadata.json` `prompt_dictionary` keys, filtered
  by the ship's `languages_served` when that is a list of language codes;
  `auto_detect` = Parakeet with more than one language, Nemotron with an
  `auto` prompt. Sizes: Hugging Face tree listing, Parakeet limited to the
  file names FluidAudio's public `ModelNames` says it downloads. Downloaded
  state and on-disk size: FluidAudio's own cache layout. Hugging Face answers are cached on disk
  (`~/Library/Caches/MeetOnTrack/stt-discovery/`) so the list works offline;
  a model whose languages are unknown is listed unavailable with the reason.
- `openai`: `GET /v1/models` with the person's key, every id listed in the
  order returned, no name filtering; `final`, `speakers` are `null` until
  `stt-check` runs. Live is not offered (no live adapter yet).
- `assemblyai`: no model list endpoint, so `model_entry` is `free_text`; the
  id is sent as `speech_models: [id]` and the transcript records the
  provider's `speech_model_used`. Live is not offered (no live adapter yet).

Sizes (MEETONTRACK-39): `size_bytes` is the model's total size,
`download_bytes` what `stt-download` would still fetch (0 when downloaded,
`null` when no file listing is known). The UI always labels a number with what
it is ("download size 460 MB") and shows no download for a model already here.

### Models already on this Mac (MEETONTRACK-45)

FluidAudio 0.15.5 loads a model only from its current folder name
(`Repo.folderName`, for example `parakeet-tdt-0.6b-v3`); it has no fallback to
the older `-coreml` name (`Repo.name`) that earlier FluidAudio releases, and
apps built on them such as FluidVoice, wrote to the same
`~/Library/Application Support/FluidAudio/Models` root. On the owner's Mac both
folders held Parakeet v3: identical encoder and decoder weights, a different
joint module (`JointDecision` vs `JointDecisionv3`) and `config.json`.

Discovery (`STTReuse.describe`) therefore looks, for every file the pinned
FluidAudio needs (from the Hugging Face tree listing), in the other folders:
both folder names under the default root and under `~/.cache/fluidaudio/Models`.
A file of the right size there counts towards `found_elsewhere`; only the rest
counts towards `download_bytes`. `stt-download` (`STTReuse.adopt`) verifies each
such file against the listing's content hash (sha256 for LFS files, git blob
sha1 otherwise) and copies it into our folder with `FileManager.copyItem`, which
clones on APFS (no extra disk); FluidAudio's downloader then skips files that
exist and fetches only what is missing. The other folder is only read: nothing
in it is changed or deleted. Sandboxed apps' containers are not scanned.
The UI shows such a model as "already on this Mac (from FluidVoice / an older
version): ready" when nothing is left to fetch, or "needs a small update
(download N MB)".

### Web API (Python, mirrors `/api/ai`)

- `GET /api/stt`: `{"ok", "choice": {"choice": stored|null, "state", "reason", "deferred": [{session, kind, reason, at}]}, "downloads": [...], "retranscribe": [...], "check": last check|null}`.
- `GET /api/stt/options[?refresh=1]`: the discovery contract above plus `best_for`.
- `POST /api/stt/choice {"choice": {...}}` (validated against the options),
  `POST /api/stt/download {"model"}` and `GET /api/stt/download`
  (job progress from `stt-download` events), `POST /api/stt/check {"choice"?}`,
  `POST /api/stt/key {"engine", "key"}`, `POST /api/stt/retranscribe {"session", "choice"?}`.

### Other commands

- `meetingcopilot stt-download --model ID --json`: the
  only code path that downloads speech models (the app otherwise runs FluidAudio
  with `ModelHub.offlineMode`). One JSON object per line:
  `{"event": "progress", "item": "model", "id": "...", "fraction": 0.4, "phase": "listing|downloading|compiling", "completed_files": 3, "total_files": 9}`,
  `{"event": "done", "item": "...", "id": "..."}`, then
  `{"event": "finished", "ok": true}` or `{"event": "error", "item": "...", "id": "...", "message": "..."}`
  (exit 1). Installers download no speech models.
- `meetingcopilot stt-check --json [--engine E --model M --language L]`
  (default: the stored choice): loads a local model and transcribes one second
  of generated audio, or sends that second to the cloud engine. Prints
  `{"contract": "meetontrack.stt-check/1", "choice": {...}, "ok": true, "steps": [{"name": "...", "ok": true, "detail": "..."}], "model_used": "...", "error": ""}`.
  Only an explicit Check runs it.
- `meetingcopilot process DIR --again [--engine E --model M --language L]`:
  re-transcribes with the stored choice, or with the given choice for this one
  run (nothing is stored).

### Deferred sessions

When there is no ready choice, the chosen model is not downloaded, the engine
is unavailable or the network fails, the session's `meta.json` gets
`transcription_deferred: {"kind": "needs_choice|unavailable|network", "reason": "...", "at": "ISO 8601"}`.
A deferred session keeps its uncompressed audio, does not consume one of the
three transcription attempts and is retried when the choice becomes ready (the
app watches `config.json`), the network returns, or the app starts. A finished
transcript clears the key. Recording never depends on the choice: without a
live-capable choice the recording runs without a live transcript and shows why.

### Live and speakers

- Live uses the chosen model: Nemotron streams; Parakeet runs FluidAudio's
  sliding window (about 13 s behind, so a pause ends an utterance only after
  one window); cloud engines show "no live transcript for this engine yet" and
  the recording continues. Live never downloads: a choice that cannot run live
  is the live status `unavailable` with its reason, exported to the assistant
  as `status: "unavailable"` and `status_reason` in the live transcript file.
- Speakers (owner decision 2026-10-21): no setting and no prompt. Cloud
  engines identify speakers themselves. Otherwise transcripts are labelled by
  channel: microphone is you, call audio is the others. Speaker diarization
  is unchanged from main: the live `RemoteSpeakerDiarizer` voice slots, the
  `--voices` path of `transcribe-audio` and the post-call `SpeakerNamer` run as
  before. Which diarizer files they use is not a person's choice: the first
  LS-EEND model present on this Mac (`LocalSpeakerModel.installed`, FluidAudio's
  variant and step order). With none present they are skipped and the channel
  labels stand. The one difference from main: main's live diarizer downloaded
  LS-EEND `dihard3`/500 ms implicitly on first use; now nothing downloads
  outside `stt-download` and the installer, so it uses only files already
  here. LS-EEND timeline thresholds stay adapter constants
  (`RemoteSpeakerDiarizer`): tuning of one adapter, not a model choice. A
  finer split of the far end in the final transcript is a separate future
  task; its hook is marked in `TranscriptionCoordinator` (`.perTrack`).
- Provenance: `transcript.json` `engine`, `model` (AssemblyAI: the provider's
  `speech_model_used`) and `language` that actually ran.

### Open questions for the owner

- Existing cloud installs without `transcription.language`: the migration
  keeps engine and model but leaves `language` for the person (a cloud model's
  languages are not known offline), so their transcripts defer until the card
  is finished. Local models get their implied language (above).
- Call audio is still labelled "Them" / "Они" as on main; the owner's wording
  was "Others". Changing the label is left to the first-run redesign.
- Nothing downloads a speaker model any more (main's live diarizer fetched
  LS-EEND on first use). Should the installer or `stt-download` fetch one so
  that live voice separation keeps working on new installs?
- OpenAI's model list is long and unfiltered (no name heuristics allowed);
  the redesigned UI may want a search box.
- Parakeet encoder precision (int8 or int4) is left at FluidAudio's own
  default rather than offered as a choice.
