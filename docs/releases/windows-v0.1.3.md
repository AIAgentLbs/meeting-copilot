# Windows technical beta 0.1.3

Corrects product branding throughout first-run setup, settings, tray menus,
notifications, recovery/configuration messages and application metadata.
The About link goes to the Meeting Copilot site; Amanu is acknowledged as
the upstream project in license attribution, not as this application's name.

```powershell
irm https://aiagentlbs.github.io/meeting-copilot/install.ps1 | iex
```

Windows 11 24H2+, x64. Unsigned technical beta; do not disable SmartScreen
or antivirus. Preserves user settings, recordings and existing Codex login.
Finish the call and close Capture before updating. No in-app updater yet.
Includes the live-worker and Codex search-path fixes from 0.1.2.
41 live tests and 141 core tests pass on the Windows reference machine.

Capture source: `4bc7f2ea870233c551c14255ff66e285f9225674`.
ZIP SHA-256: `e8ab3be8201a398fb376f78fdb68a884e3367a502a0be78194b4ebe84dbf1670`.
