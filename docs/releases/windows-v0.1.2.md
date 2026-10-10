# Windows technical beta 0.1.2

Windows 11 24H2+, x64. Unsigned beta: do not disable SmartScreen or antivirus.

```powershell
irm https://aiagentlbs.github.io/meeting-copilot/install.ps1 | iex
```

Includes self-contained Capture, native speech runtimes, embedded Python and
the web interface. Speech models download separately with checksum verification.
Uses existing Codex authorization with `gpt-6.1-sol`; no Granola is used.

Fixes the renamed live decoder executable and adds the isolated Codex search
tool directory to the application PATH. Does not replace the user's Codex.
40 native live tests pass on Windows, including the packaged worker-path test.

Recordings and settings remain in user directories across updates. Start menu
and Startup shortcuts launch the application; UI: http://127.0.0.1:43121.
Finish recording and close Capture before repeating the installer command.
In-app automatic updates are not enabled. Screen OCR/chat extraction and
delivery/PDF parity are not accepted Windows beta features yet.

ZIP SHA-256: `20d3953444d750da1ba9684645c57cdd2ee8a2a999839e1b2289440723426510`.
