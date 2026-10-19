# MeetOnTrack application repository

Owner scope decision: 2026-10-19.

- This repository owns end-user software: native capture, the local web UI,
  transcription, context retrieval, integrations, installers, packaging,
  automatic updates, tests and user documentation.
- Keep `docs/TODO.md` limited to that software scope.
- Website, domain/DNS, GA4, GSC, Umami, SEO, marketing email-domain setup,
  competitor comparisons, keyword/trademark research and promotional demos belong
  to `AIAgentLbs/meeting-copilot`, the existing Pages website repository. Its
  single website backlog is root `SITE_TODO.md` (local sibling checkout
  `../meeting-copilot/SITE_TODO.md`). Keep only a cross-reference here.
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
