# Website publication and repository separation

Date: 2026-10-19. This is website/distribution evidence, not hardware acceptance.

- Canonical website `AIAgentLbs/meeting-copilot` contains website content,
  research/SEO, Pages CI and tested installer/documentation snapshots only.
  Removed 206 application files/build workflows from its current public tree.
  Historical public source/license records remain available in Git history.
- Current application source remains in the existing private
  `AIAgentLbs/meeting-copilot-private-copy`; native Windows source remains in the
  existing private `AIAgentLbs/amanu-private-copy`. Neither was made public.
- Existing diverged local application work was preserved in local Git recovery
  references and a named stash before switching this checkout to the website-only
  branch. It was neither discarded nor pushed into the website release.
- Pages revision `e58be700c51509481124b33778a30a08fef827c1` deployed successfully:
  https://github.com/AIAgentLbs/meeting-copilot/actions/runs/39311482254
- Anonymous HTTPS checks passed for apex, www redirect, EN/RU and both installer
  routes. Installer bytes match the pinned repository snapshots.
- Anonymous release downloads verified:
  Mac `2df0822063ccbfd2ba14d8463664a3d5f2ae83ebfd31877cff47d89558c32593`;
  Windows `3126a3fc819bb80d1ddd762ce14310d42bf99ae3b974983f0872fdcff39026c9`.
- Mike's Chrome rendered the live domain, both platform install actions and the
  Windows installer command. Clicking Copy showed the PowerShell success status.
  Site screenshots remain outside Git; no private transcript was used.
- Claude Opus 5.5 independently fetched all three public pages (site + releases)
  and confirmed the install instructions and public technical-beta availability.
  It did not download archives; the separate anonymous SHA checks above did.
- Gemini 3.8 Flash High verification was attempted but returned no verdict within
  the bounded run and was stopped. Only the actual Claude-family web check counts
  as an independent model check from this Codex host; do not claim three-family
  agreement. Mechanical anonymous URLs and hashes provide the availability proof.
- Follow-up corrected EN/RU instructions: no second launch command. The installer
  opens the browser after the actual local health response. 13 installer tests
  and 370 Swift tests passed; installed native Open MeetOnTrack assistant was
  clicked and opened the local page in Mike's Chrome. Immutable archives retained.
- Final publication acceptance: Pages run
  https://github.com/AIAgentLbs/meeting-copilot/actions/runs/39312712070
  deployed `065376da1443dffeaf4cb037287aa09cf0b88d22`. Both EN/RU pages and
  installer routes were fetched anonymously again and match the repository
  byte-for-byte. Both public archives were downloaded again and their hashes
  still match the accepted values above. Later ownership/evidence-only commits
  do not change the deployed site files or require another rollout.
- Final application CI at installer revision
  `0d15b89b153ef9fce63a8e11fcb2bbf20e79a748` succeeded:
  https://github.com/AIAgentLbs/meeting-copilot-private-copy/actions/runs/39312643893

Downloadable beta does not mean real-device audio acceptance: the physical
Windows host was offline; clean-machine Mac/audio/reconnect gates remain in the
software repository. Mac is ad-hoc/not notarized and Windows unsigned. Do not
disable OS security. No DNS, analytics or mail-account mutation was needed for
this release; their remaining acceptance is tracked in `SITE_TODO.md`.
