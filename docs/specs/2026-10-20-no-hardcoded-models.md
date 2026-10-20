# No hardcoded AI or speech providers, models or modes

Owner rule 2026-10-20 (see `AGENTS.md`). Status: phase 1 implemented 2026-10-20
(Python layer `copilot/web/ai_providers.py`); phases 2-4 planned. Backlog: `docs/TODO.md`.

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
  `~/.config/meeting-copilot/config.json` (owner decision 2026-10-20; no separate
  `ai.json`). The AI choice lives under the top-level `ai` section:
  `{"ai": {"purposes": {"live_analysis": {"provider", "model", "effort", "speed"}, ...}}}`.
  Schema: [`docs/config.schema.json`](../config.schema.json).
- Ownership: each component writes only its own sections. The Python web server
  owns `ai`; Swift (`Config.update`) and the Windows installer / C# recorder
  (`AppSettingsStore`, same path) own the capture sections. Every writer does
  read-modify-write of the whole file, keeps keys it does not own, takes the
  advisory lock `config.json.lock`, writes a temp file in the same folder and
  replaces atomically, keeping the file mode (0600 when new). A writer never
  replaces a file it cannot parse.
- Known gaps in the other writers (2026-10-20 review, not changed in phase 1):
  Swift `Config.update` (`capture/Sources/meetingcopilot/Config.swift:550-566`)
  keeps unknown top-level keys, so `ai` survives, but it takes no lock
  (lost update if Python writes between its read at :552 and write at :563),
  `Data.write(.atomic)` at :617 resets the file mode, and a malformed file reads
  as `[:]` (:508-519, :526) so the next Swift save drops every other section.
  `AppSettingsStore` is not in this repository; its behaviour is unverified.
- Phase 1 purposes: `live_analysis` (analysis, chat and the context planners),
  `live_translation`, `frame_relevance`, `summary_rewrite`. Speed `""` means
  standard; effort is required whenever the provider lists levels for the model.
- No silent default: if a purpose has no valid choice, the UI asks. A stored
  choice the installed provider no longer offers is shown as unavailable with
  the reason (old CLI, plan, not signed in).
- Check AI tests the chosen combination per purpose and records the model the
  provider reports it used.
- STT: an engine registry for final, live, retranscription and diarization,
  engine and model chosen by the user, options discovered from the engine.

## Phases

1. Python AI provider layer + discovery + per-purpose selection UI + Check AI;
   remove all model ids from Python, JS and UI text. Release 0.1.11. Done
   2026-10-20 except the release itself.
2. Swift summary/naming reads `ai.json`; remove code defaults and fixed order;
   pass the model to Claude CLI.
3. STT engine registry on Mac (live, final, retranscription, diarization).
4. Windows: launcher, installer and the C# recorder follow the same rule.

## Phase 1 implementation notes (2026-10-20)

- Discovery is lazy and cached per provider (5 min when available, 30 s when
  not; "Refresh lists" forces it), with a timeout per call; failures become
  `unavailable: <reason>`. Nothing runs at import or server start.
- A provider session (Codex thread, Claude session, Antigravity conversation)
  is resumed only by the same provider/model/effort/speed choice that opened it.
- Model recorded: Claude and Antigravity report the model that ran (stream
  `init`); Codex `exec --json` and Ollama report nothing beyond the request, so
  the requested id is recorded.
- Safety per adapter: Codex keeps `--sandbox read-only`, `--ask-for-approval
  never`, `--ignore-user-config`, and disables shell/MCP/skills/web search for
  purposes that need no files. Claude runs with `--setting-sources ""`,
  `--strict-mcp-config` and only `Read,Grep,Glob` (or no tools). Antigravity
  runs `--mode plan --sandbox` in an empty folder, but its print mode still
  reports `permission_mode: always-proceed`; read-only is not provable there
  (open item in `docs/TODO.md`). Ollama has no tools.
