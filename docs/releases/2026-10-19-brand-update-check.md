# Icon refresh and manual update notice acceptance

## Scope and current outcome

- Mac installed locally, not a new public release. Owner confirmed the Dock
  and menu-bar icons changed on 2026-10-19.
- The existing MeetOnTrack M-and-dot mark replaces the waveform and the legacy
  feather generator. Menu, status/about windows and generated bundle icon share
  `BrandIcon.swift`; the bundle icon resource is named `MeetOnTrack.icns` to avoid
  reusing the old resource identity. Compatibility bundle/executable IDs remain.
- Windows icon source changed in the native capture repository's
  `windows/scripts/New-BrandIcon.ps1`. No Windows build or installed UI acceptance
  is claimed: the bounded ED25519 SSH probe did not return a host key.
- Latest owner scope: automatic installation deferred. Notifications, release
  notes and a copyable manual command remain required now.

## Verification

- Swift arm64 release build passed. This host needed its existing SDK C++ headers:
  `CPLUS_INCLUDE_PATH=/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/c++/v1`.
- Assembled bundle passed `codesign --verify --strict`; signing is still ad hoc,
  not Developer ID/notarization. No new identity or privacy reset was installed.
- 4 source-branding tests and 15 release-checker tests passed.
- `node scripts/test-update-command.cjs` passed Mac/Windows command selection,
  copy success/failure, Russian copy, notice visibility and plain-text notes.
- Chrome rendered a synthetic newer-version notice, notes and the update command
  through `scripts/preview-first-run.py --updates-fixture macos --port 43994`.
  This was isolated test state, not a published v0.1.10 release.
- Native app UI reported MeetOnTrack, ready, auto-record enabled and live
  transcript enabled after relaunch. Owner supplied actual icon visual acceptance.
- Installed web files match source. Service healthy; update checking enabled,
  no check error and no newer eligible release reported at inspection.
- Config bytes unchanged. Recordings were not touched. Capture was idle before
  replacement. Previous app and web files retained in a timestamped local backup
  outside Applications. No active call was interrupted; no audio smoke was run.

## Remaining boundaries

The command repeats the official website installer. Its version/checksum must be
published alongside each release; the UI explicitly warns that the website pin
can lag release metadata. No shell command is executed from the UI. There is no
automatic installer or new public package in this change. Windows installed
acceptance and packaging are tracked in `docs/TODO.md`.
