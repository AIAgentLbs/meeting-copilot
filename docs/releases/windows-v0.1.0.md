# Windows technical beta 0.1.0

Windows 11 24H2 or newer, x64. This is an unsigned technical beta, not a
Microsoft-signed stable release. Do not disable SmartScreen or antivirus.

The ready-to-run package includes the Meeting Copilot-specific native capture
build, .NET runtime, WASAPI capture, live/final ASR runtimes, embedded Python and
the loopback-only Copilot UI. End users do not compile source or install an SDK.
The local speech models download separately (about 1.5 GB) with pinned SHA-256.
Codex CLI must already be installed and signed in. Copilot analysis explicitly
uses `gpt-6.1-sol` with read-only sandbox and approval policy `never`.

```powershell
irm https://aiagentlbs.github.io/meeting-copilot/install.ps1 | iex
```

Installation: `%LOCALAPPDATA%\MeetingCopilot\versions`.
User data: `%USERPROFILE%\.local\share\meeting-copilot`.
Settings: `%USERPROFILE%\.config\meeting-copilot`.
Start menu: Meeting Copilot. Web UI: `http://127.0.0.1:43121`.
The same command updates the package after the published version/checksum changes.
Finish the meeting and close Capture before updating. Settings and recordings
are preserved. Automatic in-app updates are not enabled in this beta.

Capture source derives from the independently copied Amanu Windows branch.
Its identity, data, Credential Manager namespace and single-instance control are
separate from Amanu. This package does not use Granola or the author's update feed.
The unmodified ASR native runtimes are reused from the checksum-verified upstream
Windows 0.6.6 package. Their licenses and Amanu's MIT notice are included.

Native Capture revision: `1857c83f7def45e6d7662849e813e3720241d5a2`.
Copilot runtime revision: `53f551a01958ac409559e765520c311d30f06d84`.
ZIP SHA-256: `05f7b492c6bfd9fc7fc068f2700db3c0de3c4e2686a8c2906adcf245aa63f8c4`.

Windows-specific screen OCR/chat extraction, PDF/delivery parity and extended
call/reconnection soak testing are not acceptance claims of this initial beta.
