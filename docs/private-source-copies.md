# Source repositories

## Current layout — 2026-10-20 (owner decision), renamed 2026-10-21

- Public `AIAgentLbs/meetontrack` (MIT, renamed from `meeting-copilot` on
  2026-10-21): web assistant, macOS capture in `capture/`, installers,
  packaging, GitHub Releases. Local checkout directory keeps its old name.
- Private `AIAgentLbs/meetontrack-hub` (renamed from `meetontrack` on
  2026-10-21): project hub.
- Public `AIAgentLbs/meetontrack-recorder` (MIT, formerly
  `amanu-private-copy`): recorder derived from Amanu, macOS `Sources/` and
  Windows `windows/` as upstream lays them out. `master` mirrors
  `gsamat/amanu`; MeetOnTrack work is on `main` (former
  `feat/meeting-copilot-windows`). Local checkout
  `/Users/m/code/aiagentlbs/meetontrack-recorder`.
- Private `AIAgentLbs/meetontrack-website`: website, deployed by Coolify.
- `AIAgentLbs/meeting-copilot-private-copy`: merged into this repository on
  2026-10-20 and deleted by the owner on 2026-10-21.

Before publication both former private copies were scanned (gitleaks over all
refs, plus private-identifier grep over our commits): no secrets or private
data in our commits; the only finding was an upstream `env.example` already
public in `gsamat/amanu`.

The sections below are the historical 2026-10-06 and 2026-10-19 records.

## History

Created and verified 2026-10-06, by owner request. These are independently
created private repositories, not GitHub forks (`private=true`, `fork=false`,
`parent=null`). Public distribution has not been made private or rewritten.

- https://github.com/AIAgentLbs/amanu-private-copy — complete branch/tag copy of
  Amanu, including macOS and Windows source; 79 refs matched the acquisition
  snapshot before any development changes. Default branch: master.
- https://github.com/AIAgentLbs/meeting-copilot-private-copy — source history of
  our published Meeting Copilot; 11 refs matched the acquisition snapshot.
  Default branch: main. Includes the native macOS component and release v0.1.8.

Future development starts in these private copies. Upstream updates are reviewed
imports, not direct changes in the author's repository. Preserve copyrights,
licenses and third-party notices. Raw mirrors and checkouts do not copy GitHub
release attachments, issues, permissions, secrets or signing credentials.

At acquisition, inherited Actions were disabled in both copies: source workflows were retained,
but must be audited and supplied with our own release identity and settings
before they can publish anything. Existing public release feeds remain unchanged.

Windows integration baseline already examined locally:
`amanu-private-copy`, tag `windows-v0.6.5`, commit
`7d45b672a132753d2e92034c4dce7e9ae816d282`.
The copy also contains subsequent upstream tags; inspect their diff and testing
evidence before selecting a newer baseline. A source copy is not a Windows
Meeting Copilot installer or evidence of working audio capture.

Local checkouts:
`/Users/m/code/aiagentlbs/amanu-private-copy` and
`/Users/m/code/aiagentlbs/meeting-copilot-private-copy`.
At acquisition, the original dirty Mac checkout and running Capture were not replaced.
Only explicitly reviewed changes are transferred; personal recordings and
runtime settings never belong in either repository.

## Current ownership and distribution — 2026-10-19

The application repository's `main` now owns the end-user software, installers,
tests and user documentation. Website/domain/analytics/SEO/comparisons/research
belong only to the existing public `AIAgentLbs/meeting-copilot` repository.
Its earlier dirty checkout was preserved in local recovery refs/stash before
switching it to the website-only canonical main; no history was rewritten.

Both source copies remain private, independently created repositories, not forks.
The reviewed native Windows implementation is on `feat/meeting-copilot-windows`
at `b36ee3005e383c5c87ed4bceaf179ee8c95f8bb0`; do not confuse the retained
upstream `master` default with the source used for the public Windows package.
Bounded owned CI/build and packaged-install checks are now enabled and passed.
Inherited upstream signing/publishing credentials or update feeds are not used.

Public Mac and Windows 0.1.10 archives are hosted by the website repository.
See [the distribution acceptance record](releases/2026-10-19-public-distribution.md)
for immutable source identities, checksums, installer checks and the explicitly
unverified hardware/provider scenarios. A downloadable technical beta is not
evidence that all real-device or optional-account acceptance has passed.
