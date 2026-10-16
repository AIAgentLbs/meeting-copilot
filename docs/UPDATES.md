# MeetOnTrack release notifications

The local web service checks the public `AIAgentLbs/meeting-copilot` release list
once a day, first checking about 30 seconds after service startup. State polling
does not perform network requests. There is one bounded response (2 MB, 10 second
timeout), one selected release and at most 20,000 characters of release notes.
Failed requests preserve the previous notice and back off until the next day;
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
