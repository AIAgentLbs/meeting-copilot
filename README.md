# MeetOnTrack website

Public website: https://meetontrack.com/ (English) and
https://meetontrack.com/ru/ (Russian).

This repository owns the landing pages, domain/DNS, analytics, SEO, competitor
comparisons, brand research and promotional materials. Use [SITE_TODO.md](SITE_TODO.md)
as the single website tracker and [AGENTS.md](AGENTS.md) for ownership rules.

Application development, capture, transcription, integrations, installers,
update checks and end-user runtime tests belong to
[AIAgentLbs/meeting-copilot-private-copy](https://github.com/AIAgentLbs/meeting-copilot-private-copy).
Current application source is maintained in the private software repositories.
Earlier publicly published application revisions remain available in Git history.

## Website sources and publication

- `docs/` contains public EN/RU HTML, styles, scripts, SEO metadata and privacy copy.
- `docs/compare/` contains generated comparison HTML and internal evidence inputs.
- `docs/research/`, `docs/design/` and `planning/` contain website research and handoffs.
- `scripts/` contains comparison generation, website checks and asset staging.
- `.github/workflows/pages.yml` stages the explicit public-file allowlist in `_site/`.
  Research, evidence JSON, design notes and task trackers are not published pages.
- `install.sh` and `docs/install.ps1` are published installer snapshots matched to
  accepted release packages. Change pins/checksums only with package acceptance.
  Installer implementation belongs to the application repository.

The 2026-10-19 separation moved 37 files from the software checkout. Exact paths
and SHA-256 values are recorded in
[the transfer manifest](planning/2026-10-19-repository-separation.json).
No DNS, analytics, account changes or live deployment are implied by that migration.

## Local checks

```sh
node --check docs/site.js
node --check docs/analytics.js
node scripts/build-comparisons.cjs --check
node scripts/test-comparisons.cjs
bash -n install.sh
python3 scripts/test_installer.py
```

For synthetic product screenshots, run `node scripts/serve-marketing-demo.cjs`.
It reads UI assets from the sibling application checkout. To use an unpacked
release instead, set `MEETONTRACK_WEB_ROOT` to its `web/` directory. The fixture
contains synthetic dialogue only and never loads the user's settings or recordings.
Binary screenshots/logos are fetched into build artifacts from checksum-pinned
asset manifests. Keep generated media out of Git.

Before publication, inspect this checkout's branch/status and current remote main.
Preserve existing dirty application work and reconcile diverged history through
reviewed commits; do not publish the checkout wholesale.

## License

See [LICENSE](LICENSE). Preserve product-mark ownership and mandatory third-party
attribution when preparing website or distribution assets.
