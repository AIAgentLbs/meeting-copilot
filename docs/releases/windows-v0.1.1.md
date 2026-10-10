# Windows technical beta 0.1.1

Windows 11 24H2 or newer, x64. Unsigned technical beta, not a
Microsoft-signed stable release. Do not disable SmartScreen or antivirus.

```powershell
irm https://aiagentlbs.github.io/meeting-copilot/install.ps1 | iex
```

Ready-to-run Capture, .NET, WASAPI capture, local ASR runtimes, embedded Python
and the Copilot web UI are included. No SDK or user-side compilation is needed.
Local speech models download separately (about 1.5 GB), verified by SHA-256.
An existing signed-in Codex CLI is required. If npm is available, the installer
adds Codex 0.160.1 under this product's own tools directory without replacing a
parallel user's Codex installation or changing its authentication.
Analysis explicitly uses `gpt-6.1-sol`, read-only sandbox and approval `never`.

Compared with the initial 0.1.0 package, this version fixes PowerShell treatment
of Codex login-status stderr and discovers the compatible isolated native CLI.
The installer uses the embedded Python TLS client for model downloads where
Windows Schannel fails. Certificate verification remains enabled.

Install: `%LOCALAPPDATA%\MeetingCopilot\versions`.
Data/recordings: `%USERPROFILE%\.local\share\meeting-copilot`.
Settings: `%USERPROFILE%\.config\meeting-copilot`.
Start menu: Meeting Copilot. Web UI: `http://127.0.0.1:43121`.
Finish the call and close Capture before repeating the command to update.
Settings and recordings are preserved. In-app automatic updates are not enabled.

This Capture build derives from our independent Amanu source copy. Its process
identity, data, Credential Manager namespace and same-user control pipe are
separate from Amanu. It uses neither Granola nor the original author's updater.
Unmodified ASR native libraries come from the checksum-verified Windows 0.6.6
package. All included upstream license notices are preserved.

Native Capture revision: `1857c83f7def45e6d7662849e813e3720241d5a2`.
Copilot runtime revision: `6b4dd8680ab1a8508fa81a3643065e62bfcaa765`.
ZIP SHA-256: `89c600f994e37c1522f0bc1c9ad191a7860c6103269b3323cf8d1a2bb0220266`.

Windows screen OCR/chat capture, PDF/delivery parity, and extended real-call
reconnection testing remain outside this initial beta's acceptance claims.
