# MeetOnTrack release notifications

The local web service checks the public `AIAgentLbs/meeting-copilot` release list
every 15 minutes, first checking about 30 seconds after service startup. State polling
does not perform network requests. There is one bounded response (2 MB, 10 second
timeout), one selected release and at most 20,000 characters of release notes.
Failed requests preserve the previous notice and retry after 5, 10, 20, 40,
then at most 60 minutes. A successful check restores the 15-minute interval;
manual checks remain available in Settings.

The check sends no meeting content, account credentials or usage statistics.
GitHub necessarily receives the ordinary network request, including the client's
IP address. Settings → MeetOnTrack updates can disable background checks. A
manual check still works when background checks are disabled.

## Version and channel identity

- macOS: the installer retains the package's `release.json` next to `web/`.
  Legacy installations fall back to the installed Capture bundle's version;
  existing unsigned macOS installs are treated as technical beta.
- Windows: `release.json` already lives next to `web/` in each version directory.
- Unknown versions do not trigger network checks or offer a possible downgrade.
- Technical-beta installs accept beta releases; stable installs exclude them.
  Both require a newer numeric version and a matching platform asset. Publishing
  a new build at an existing version is not supported: increment the version.
- Expected tags/assets currently remain `vX.Y.Z` / `meeting-copilot-macos.zip`
  and `windows-vX.Y.Z` / `meeting-copilot-windows-vX.Y.Z-x64.zip`. Changing
  distribution names requires updating the selector and tests in the same release.

## User experience and safety

A new version displays a header notification. Clicking it opens Settings with
the version, release notes, and the official release page. Dismissal persists
across service restarts; notes remain accessible in Settings. Notes are rendered
as plain text, never as HTML. This is an in-app notice, not an OS notification.

This feature never downloads executables, installs updates, quits the app, or
restarts recording. The user opens the release instructions and installs after
the call. Native Sparkle installation stays disabled until a signed appcast and
signing/recovery acceptance are available. Existing users receive this checker
only after installing a package that includes it.

## Automatic installation: release-blocking requirement

Developer ID app signing/notarization and Sparkle Ed25519 update-archive signing
are separate mechanisms. Apple Developer membership is not a prerequisite for
the latter, nor for serving an HTTPS appcast and update archives. Developer ID
remains a distribution-hardening goal; command-line installation does not remove
macOS execution and permission checks. Do not claim that membership alone fixes
recording permissions, or block updater implementation solely on enrollment.
Validate the actual package's launch, framework loading and recording permissions
across an update. References: https://sparkle-project.org/documentation/ and
https://developer.apple.com/developer-id/ (checked 2026-10-19).

Owner requirement (2026-10-19): beta users must receive fixes automatically,
without repeating the website installation command for each release. The faster
checker above is NOT an automatic installer and does not satisfy that requirement.

The release must update Capture, web UI and embedded Python as a single unit.
macOS currently installs these into separate locations; simply enabling Sparkle
would leave the web service behind. Windows ZIP installs are not registered with
Velopack, so its existing update service reports NotInstalled.

Required acceptance before promotion:

- Package the complete product in the native update unit (Sparkle on Mac,
  Velopack on Windows), using our own feed and signing identity, never upstream.
- Automatically check, download and verify promoted releases; expose release
  notes and progress, and let users disable automatic installation in Settings.
- Defer replacement while recording, paused, starting, finalizing, transcribing,
  archiving or delivering. Recheck under a shared lifecycle gate immediately
  before exit; stale web transcript state is not an installation lock.
- Preserve recordings, models, credentials and settings. Retain the last working
  version; restore it if the new native app or loopback service fails its health check.
- Test exact N-to-N+1 package updates on both OSes: background detection, active
  call deferral, tampered package rejection, offline retry, interrupted install,
  rollback and settings/data preservation. Validate native AND web versions.
- Publish the bootstrap release only after those tests. Legacy packages without
  an updater necessarily require one initial upgrade; future fixes do not.

Environment checked 2026-10-19: macOS reports zero valid code-signing identities.
Vault searches for MeetOnTrack, Sparkle, signing and Apple Developer returned no
matching records. Windows appears online in Tailscale, but a bounded ED25519 SSH
host-key probe returned no key; authenticated Windows testing was not possible.
These observations are not proof that an Apple account or another Windows access
path does not exist. Do not change the public site's manual-update disclaimer or
claim automatic installation until the complete release passes acceptance.

The visible product is **MeetOnTrack by aiagentlbs.com**. Bundle identifiers,
executable names, installation directories, launch-agent labels and configuration
keys retain their legacy names for compatibility and recording permissions.

## Reproducible tests

```sh
python3 -m unittest discover -s copilot/web -p 'test_*.py'
python3 -m unittest scripts/test_installer.py
PLAYWRIGHT_MODULE=/path/to/playwright node scripts/test-update-ui.cjs
```

The UI test uses synthetic releases and an isolated browser. It never talks to
the running meeting service. Screenshots go to `/tmp`, not Git.
