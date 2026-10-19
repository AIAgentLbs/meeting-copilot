# MeetOnTrack website backlog

Owner: `AIAgentLbs/meeting-copilot` (existing GitHub Pages website repository).
Scope correction: 2026-10-19. This is the single tracker for the website and its
domain, analytics, SEO, comparisons and marketing. Migrated from the application
backlog; these are outstanding verification/work items, not claims of failure.

Application development is tracked in `AIAgentLbs/meeting-copilot-private-copy`
(`../meeting-copilot-private-copy/docs/TODO.md` in the local sibling checkout).
Native installers and auto-updates are application work; presenting their tested
downloads on the website is website work. Do not duplicate either backlog.

## Domain, analytics and search

- [ ] Close the authorized domain/HTTPS/DNS launch acceptance using the current
  live site and canonical Pages branch; verify apex/www, redirects and sitemap.
  Do not infer the live state from this older dirty checkout.
- [ ] Finish and independently verify GA4, Google Search Console and Umami setup,
  collection/reporting and ownership; keep privacy copy consistent with actual
  collection. Do not invent measurement IDs or count configuration as collection.
- [ ] Finish the authorized domain contact-email and optional sending-service
  setup; independently verify existing records and delivery before changes.
  Do not create extra paid mailboxes or change unrelated domain records.
- [ ] Verify canonical URLs, indexing directives, sitemap, metadata, structured
  data, EN/RU navigation and mobile SEO on the published domain.
- Private operational evidence remains in the existing
  [operations handoff](https://github.com/AIAgentLbs/operations/blob/main/docs/meetontrack-domain-launch-2026-10-15.md).
  That record is evidence, not a second task tracker. Never copy credentials,
  account identifiers or private operational records into this public repository;
  use approved Vault access for secrets. Verify that handoff's publication before
  relying on the remote link; it was previously local-only.

## Comparisons, keywords and brand research

- [ ] Maintain all competitor comparison pages, including Granola, Fireflies,
  Bluedot, tl;dv and MeetScribe/Meetily. Recheck capabilities, limitations,
  open-source/licensing claims and changed plans against primary sources before
  publication; keep unsupported claims explicitly unverified.
- [ ] Preserve the owner's presentation requirements: pros/cons and meaningful
  differences, product logos, plain MeetOnTrack naming, no comparison-page links
  added to main-site navigation, and no external source deep-links in published
  comparisons beyond a product's main page. Keep verification sources internal.
- [ ] Refresh comparison `checkedAt`, regenerate affected pages and run source,
  comparison and site checks. In particular, do not turn unknown Granola
  full-product OSS rights or tl;dv native-mobile support into categorical claims.
- [ ] Validate regional search terms and map them to relevant website pages.
  MeetOnTrack / meetontrack.com is already the owner's selected name/domain;
  do not reopen naming or buy another domain without a new request.
- [ ] Perform trademark/confusion screening in the intended markets. Do not
  present domain ownership or keyword research as trademark clearance.

## Website usability and promotion

- [ ] Verify prominent Mac and Windows download/installation entry points,
  accurate prerequisites and update guidance against the exact tested packages.
  Do not advertise unshipped updater functionality or technical archives as
  accepted installers. Avoid duplicating application implementation tasks here.
- [ ] Prepare a short authentic end-to-end demo and legible screenshots showing
  launch, context connection, recording and a useful answer, with synthetic or
  explicitly approved content. Store binary media outside Git with asset links.
- [ ] Check first-time-user comprehension of the website installation journey,
  English-first copy, responsive layout and accessibility.

## Repository boundary cleanup

- [x] 2026-10-19: moved 37 website/source/research/tooling files out of the
  software checkout, verified their SHA-256 hashes, and restored this checkout's
  website files against current public main. Preserved unrelated dirty work.
  See `planning/2026-10-19-repository-separation.json` for the transfer record.
  Application Windows installer source moved to `scripts/windows/install.ps1`
  there; this site's `docs/install.ps1` remains the tested public snapshot.

- [x] Prepared the website-only publication tree with only the Pages workflow;
  application source and software build/release workflows belong in the private
  application repositories. Historical public revisions remain in Git history.
- [x] Matched Mac and Windows installer snapshots to the accepted 0.1.10 archives;
  both packages passed fresh/repeat-install preservation and checksum checks.
  Updated prerequisite and manual-update guidance without promising auto-install.
- [x] 2026-10-19: Mac and Windows 0.1.10 releases are public. Anonymous downloads
  match the accepted archive hashes; both domain installer snapshots match the
  repository byte-for-byte. Pages run `39311482254` deployed `e58be700` successfully.
  Apex and www resolve to HTTPS apex, EN/RU return 200. Mike's Chrome shows both
  platform install choices; Windows copy button displays the PowerShell success
  confirmation. Physical Windows audio acceptance remains in the software backlog.
- [x] Added a CI boundary regression: website tree must contain no `capture/`,
  `copilot/` or software workflows, while retaining both installer snapshots.
