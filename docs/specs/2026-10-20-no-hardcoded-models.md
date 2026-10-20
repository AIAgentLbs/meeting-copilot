# No hardcoded AI or speech providers, models or modes

Owner rule 2026-10-20 (see `AGENTS.md`). Status: planned. Backlog: `docs/TODO.md`.

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
- Settings source: `~/.config/meeting-copilot/ai.json`, owned by the Python
  web UI (exists on Mac and Windows); Swift reads it for summary and naming.
- No silent default: if a purpose has no valid choice, the UI asks. A stored
  choice the installed provider no longer offers is shown as unavailable with
  the reason (old CLI, plan, not signed in).
- Check AI tests the chosen combination per purpose and records the model the
  provider reports it used.
- STT: an engine registry for final, live, retranscription and diarization,
  engine and model chosen by the user, options discovered from the engine.

## Phases

1. Python AI provider layer + discovery + per-purpose selection UI + Check AI;
   remove all model ids from Python, JS and UI text. Release 0.1.11.
2. Swift summary/naming reads `ai.json`; remove code defaults and fixed order;
   pass the model to Claude CLI.
3. STT engine registry on Mac (live, final, retranscription, diarization).
4. Windows: launcher, installer and the C# recorder follow the same rule.
