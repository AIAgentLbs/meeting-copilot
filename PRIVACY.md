# Privacy

Meeting Copilot is local-first. The UI listens on the loopback interface only.
Audio files, screenshot files, repository manifests and generated reports stay
on the Mac unless the user explicitly configures external delivery. Transcript
text and OCR excerpts may be sent to the authenticated Codex CLI for chat and
automatic analysis.

For live English translation, macOS detects the transcript language locally.
Only transcript text detected as neither Russian nor English is sent through
the authenticated Codex CLI for translation; raw audio is not sent by this
feature. The original text remains available beside the English translation.
The existing chat and automatic analysis also use Codex with meeting text.

Repository access is read-only by product design. Meeting Copilot records paths,
current branches, HEAD revisions and working-tree status; it does not change or
synchronize repositories.

Before sharing logs or bug reports, remove transcripts, screenshots, participant
details, repository paths and configuration files. Never publish files from
`~/.config/meeting-copilot` or `~/.local/share/meeting-copilot`.
