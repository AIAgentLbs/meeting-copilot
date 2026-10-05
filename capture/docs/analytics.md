# Optional usage statistics

The inherited native analytics implementation is opt-out: it is on unless
`analytics` is false in configuration. The setup/settings switch and
`meetingcopilot analytics off` disable it. Opting out removes the pending
queue; changing that switch is not itself reported.

Its configured endpoint is `https://stats.meetingcopilot.me/api/batch`.
The implementation sends a stable random installation identifier, event names,
closed-vocabulary settings, coarse duration buckets and machine/app versions.
It does not include audio, transcript text, summaries, meeting names, user
names, credential contents, arbitrary model identifiers or filesystem paths.
This is a disclosure of what the current source sends, not an independent
audit of the remote server's retention or network logs.

## The events

- Installation: `installed`, `version_seen`.
- Setup/UI: `setup_opened`, `settings_opened`, `setup_completed`,
  `mic_granted`, `mic_denied`, `system_audio_heard`, `system_audio_silent`.
- Recording: `recording_started`, `recording_start_failed`,
  `recording_finished`, `recording_discarded`, `system_track_silent`,
  `session_interrupted`.
- Processing: `transcript_finished`, `transcript_fallback`,
  `transcript_failed`, `summary_finished`, `summary_backend_failed`,
  `summary_failed`, `speaker_names_finished`, `speaker_names_failed`.
- Models: `model_download_started`, `model_download_finished`,
  `model_download_failed`.
- Interaction: `artifact_opened`, `setting_changed`.

## Event fields

`trigger`, `surface`, `duration_bucket`, `live_used`, `system_audio`,
`engine`, `backend`, `model`, `fallback_used`, `from_engine`,
`to_engine`, `component`, `outcome`, `asset`, `artifact`, `reason`,
`setup_version`, `key`, `value`.

Only toggles and fixed-choice settings can produce a settings event. Text,
numbers, lists, paths and the analytics switch itself are excluded. Current
reason vocabulary: `no_network`, `no_key`, `no_model`, `usage_limit`,
`audio_missing`, `audio_too_short`, `refused`, `timed_out`,
`http_error`, `quit`, `unknown`.

## Installation fields

`analytics_schema_version`, `app_version`, `macos_version`, `arch`,
`interface_language`, `live_transcription`, `speaker_names`,
`auto_record`, `transcription_engine`, `transcription_enabled`,
`transcription_cloud_provider`, `summary_backend`, `summary_enabled`,
`speaker_names_backend`, `keep_audio`.

## Local identity and forgetting

`~/.config/meeting-copilot/analytics.json` stores the random identifier;
`~/.config/meeting-copilot/analytics-pending.json` stores unsent events. The
queue has a 500-event limit and expires entries older than seven days.
Disable analytics before removing those two files if you do not want a new
identifier created. This does not delete recordings or your other settings.
Removing local identity is not deletion of records already accepted remotely.
The analytics command prints the identifier needed to request remote deletion.

Historical design reference `specs/2026-08-22-analytics-design.md` is not
bundled in this fork. This page and the checked-in analytics catalogue describe
the current implementation.
