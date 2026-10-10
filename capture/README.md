# Meeting Copilot Capture

Native macOS capture and transcription component for Meeting Copilot by
AI Agent Labs. It captures microphone and system audio without joining the
meeting as a bot and publishes an atomic local transcript snapshot for the
loopback-only copilot UI.

## Build

Requires macOS 15, Xcode command-line tools and Swift 6.

```sh
swift test
make app
```

The application bundle is written to `.build/MeetingCopilotCapture.app`.
Microphone and Screen & System Audio Recording permissions are granted by the
user in macOS System Settings.

## Data

The live transcript is written to:

`~/.local/share/meeting-copilot/meeting-copilot-live.json`

The snapshot contains text and timestamps, not audio or credentials, and is
created with user-only permissions.

## Configuration reference

Settings are stored in `~/.config/meeting-copilot/config.json`. The setup and
settings windows expose the same schema; API-key settings contain file paths,
not credentials to paste into this documentation.

- Automatic capture: `auto_record.enabled`, `auto_record.mic_activity`,
  `auto_record.calendar`, `auto_record.start_delay_seconds`,
  `auto_record.stop_delay_seconds`, `auto_record.min_duration_seconds`,
  `auto_record.silence_stop_minutes`, `auto_record.max_duration_minutes`,
  `auto_record.apps`, `auto_record.ignore_apps`.
- Audio/storage: `system_audio`, `mic_voice_processing`,
  `offline_echo_cancellation`, `keep_audio`, `recordings_dir`.
- Recognition: `transcription.enabled`, `live_transcription.enabled`,
  `transcription.engine`, `transcription.cloud`, `transcription.language`,
  `transcription.model`, `transcript_echo_filter`,
  `transcription.assemblyai.api_key_path`,
  `transcription.assemblyai.speech_model`, `transcription.openai.model`.
- Summaries: `summary.enabled`, `summary.backend`, `summary.model`,
  `summary.openai_model`, `summary.ollama_model`, `summary.language`,
  `summary.api_key_path`, `summary.openai_api_key_path`.
- Context and speakers: `calendar`, `calendar_provider`,
  `speaker_names.enabled`, `user_name`, `speaker_names.backend`,
  `speaker_names.model`.
- Interface/behavior: `interface_language`, `dock_icon`, `menu_bar_icon`,
  `window`, `on_stop`.

Short automatic recordings use a 300-second minimum by default; intentional
manual recordings are preserved. Interface language is chosen on first
launch and is separate from speech/summary language. This distribution does
not collect or send product-usage statistics.
