# MeetOnTrack application repository

Owner scope decision: 2026-10-19.

- This repository owns end-user software: native capture, the local web UI,
  transcription, context retrieval, integrations, installers, packaging,
  automatic updates, tests and user documentation.
- Keep `docs/TODO.md` limited to that software scope.
- Tasks for all MeetOnTrack repositories live in the maintainer's private
  tracker (project `MEETONTRACK`, owner decision 2026-10-21). `docs/TODO.md` mirrors
  it: every open item carries its `MEETONTRACK-N` number. Add new work to the
  tracker first, then the mirror line; close it in the tracker.
- Website, domain/DNS, GA4, GSC, Umami, SEO, marketing email-domain setup,
  competitor comparisons, keyword/trademark research and promotional demos belong
  to the private `AIAgentLbs/meetontrack-website` repository, deployed by
  Coolify on 5.78.46.146 (owner decision 2026-10-20). Its single website backlog
  is root `SITE_TODO.md` (local sibling checkout
  `../meetontrack-website/SITE_TODO.md`). Keep only a cross-reference here.
- This repository is the public `AIAgentLbs/meeting-copilot`. It also hosts the
  GitHub Releases that the website download links point to. Never commit
  secrets, private client data or meeting recordings.
- No hardcoded AI or speech providers, models or model modes anywhere (owner
  rule 2026-10-20). Provider (Codex, Claude Code, Gemini, local runtimes such as
  Ollama), model, reasoning effort, fast/speed mode, and speech-to-text engine and
  model (Parakeet, AssemblyAI, OpenAI, future engines) are user choices. Options
  come from what is installed, signed in and supported by the user's plan, read
  from the provider itself, never from a fixed list in code. Code may hold engine
  adapters, not chosen models; a missing choice is asked for, not defaulted.
  The AI is chosen once (`ai.choice`) and every AI task uses it (owner decision
  2026-10-21); a task the choice cannot do is unavailable with the reason.
- One settings store for every component (owner rule 2026-10-20): the Swift
  Mac app, the C# Windows recorder and the Python web server all read and write
  `~/.config/meeting-copilot/config.json` (Windows:
  `%USERPROFILE%\.config\meeting-copilot\config.json`) with one shared schema
  and one vocabulary. Writers change only their keys with an atomic
  read-modify-write and preserve every other key. No parallel settings files
  for the same choice.
- Do not add website/marketing acceptance to the application's release gate.
  The app owns a functioning installer and update artifacts; the website owns
  how their download links, instructions and claims are presented.
- Website sources, research and the Pages workflow were moved out on 2026-10-19.
  Do not reintroduce them here. Historical Git revisions retain their old files;
  the current checkout contains application work only. The website repository's
  `planning/2026-10-19-repository-separation.json` records file hashes and ownership.
- Windows installer source is `scripts/windows/install.ps1`, macOS is `install.sh`.
  Packaging and tests must use these application-owned sources. The website may
  publish a tested installer snapshot matched to a public package and checksum.
- Preserve required upstream licence attribution and compatibility identifiers.
  Do not confuse product branding with deleting legal notices or data paths.
