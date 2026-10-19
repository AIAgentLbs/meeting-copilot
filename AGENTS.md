# MeetOnTrack website ownership

Owner scope decision: 2026-10-19.

This existing GitHub Pages repository owns the public MeetOnTrack website,
domain/DNS launch work, analytics, SEO, competitor comparisons, keyword and
trademark research, and promotional material. Use root `SITE_TODO.md` as the
single task tracker for those concerns.

Application implementation and end-user runtime acceptance belong to
`AIAgentLbs/meeting-copilot-private-copy` and its `docs/TODO.md`. Application source
and build workflows are removed from the website's current tree. Preserve earlier
published Git history and any saved local work; keep release hosting and download
links working. Do not copy private application code into this public repository.

Inspect branch/status and current canonical website revision before publishing.
The earlier dirty application work and diverged local main were preserved in
local `recovery/` branches, a named stash and
`refs/recovery/pre-site-separation-20261019-stash`. The active `main` checkout
now follows the website-only remote tree. Do not restore those application
files into this repository or publish a recovery branch wholesale. Never discard
saved work. This scope decision is not permission to alter DNS/accounts or
publish unreviewed files.

Secrets stay in the approved Vault; private operational evidence stays in
`AIAgentLbs/operations`. Keep only a reference here, not private account records
or a duplicated operational backlog.
