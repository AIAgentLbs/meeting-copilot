# Windows technical beta 0.1.4

Removes product-usage statistics completely from the Windows application:
the setup checkbox and Advanced entry, sender, periodic flush, installation
identifier, pending queue, event hooks and usage configuration property.
The update removes the retired configuration key and local identity/queue files
while preserving other settings and all meeting recordings.

```powershell
irm https://aiagentlbs.github.io/meeting-copilot/install.ps1 | iex
```

Windows 11 24H2+, x64. Unsigned technical beta. Finish the meeting and close
Capture before updating. Do not disable SmartScreen or antivirus.
Recording, transcription, recovery and optional model/API operations remain
available; removing usage statistics does not make the entire application offline.
137 core tests and 41 live tests pass on Windows. Five installer fixture checks
verify installation, settings preservation, retired setting/state removal and
bad-checksum rejection.

Capture source: `cedcb0b8f179f93dba35d81a76674e0dea1cb66b`.
ZIP SHA-256: `74b2c0deb0374eac4df854188f5744a1f5971b60fb0cd52b3413265335f2c828`.
