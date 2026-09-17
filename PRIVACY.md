# Privacy

Meeting Copilot is local-first. The UI listens on the loopback interface only.
Audio, transcripts, frames, notes, repository manifests and generated reports
stay on the Mac unless the user explicitly configures an external delivery or
AI service.

Repository access is read-only by product design. Meeting Copilot records paths,
current branches, HEAD revisions and working-tree status; it does not change or
synchronize repositories.

Before sharing logs or bug reports, remove transcripts, screenshots, participant
details, repository paths and configuration files. Never publish files from
`~/.config/meeting-copilot` or `~/.local/share/meeting-copilot`.

