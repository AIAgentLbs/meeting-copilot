# Privacy

Meeting Copilot is local-first. The UI listens on the loopback interface only.
Product-usage statistics are not collected or sent. There is no telemetry
switch, installation tracking identifier, event queue or usage-reporting sender.
Audio files, repository manifests and generated reports stay on the Mac unless
the user explicitly configures external delivery. AI features use the AI tool
(Codex, Claude Code or a local Ollama) and model the user chose for each task
in Getting started; nothing is sent to an AI tool for a task without a choice.
Transcript text, OCR excerpts and connected-source excerpts may be sent to the
tool chosen for chat and automatic analysis, and a screenshot may be sent to
the tool chosen for screenshot relevance. A local Ollama model keeps that data
on the computer; Codex and Claude Code send it to their cloud service under
the user's own account.

For live English translation, macOS detects the transcript language locally.
Only transcript text detected as neither Russian nor English is sent to the
tool chosen for live translation; raw audio is not sent by this feature. The
original text remains available beside the English translation.

Repository access is read-only by product design. Meeting Copilot records paths,
current branches, HEAD revisions and working-tree status; it does not change or
synchronize repositories.

Before sharing logs or bug reports, remove transcripts, screenshots, participant
details, repository paths and configuration files. Never publish files from
`~/.config/meeting-copilot` or `~/.local/share/meeting-copilot`.
