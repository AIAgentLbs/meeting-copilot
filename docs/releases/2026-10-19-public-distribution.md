# Public MeetOnTrack 0.1.10 distribution acceptance

Date: 2026-10-19. Downloadable technical beta, not a stable/hardware-certified
release. Website ownership and presentation are tracked only in the website
repository; this document records software/archive acceptance.

## Immutable package identity

Both packages embed application revision
`ae27f2b8a323a1b7d20db3a6ef23e1345cb4249b`.
Installer/CI pins were committed as `a1bdc66fd30402aed2a24655b88b110331e39c56`
and promoted to private application main after CI success.

- Mac public tag `v0.1.10`, archive `meeting-copilot-macos.zip`, SHA-256
  `2df0822063ccbfd2ba14d8463664a3d5f2ae83ebfd31877cff47d89558c32593`.
- Windows public tag `windows-v0.1.10`, archive
  `meeting-copilot-windows-v0.1.10-x64.zip`, SHA-256
  `3126a3fc819bb80d1ddd762ce14310d42bf99ae3b974983f0872fdcff39026c9`.
- Windows native revision `b36ee3005e383c5c87ed4bceaf179ee8c95f8bb0`;
  integrated version 0.1.10, independent native component version 0.6.6.

Both archives were downloaded anonymously after publication and matched these
hashes. No runtime credentials, recordings, repository manifests or meeting data
were used as package inputs. Generated archives/icons are artifacts, not new
Git binaries. Upstream notices and compatibility storage identifiers remain.

## Checks

- 369 Swift tests / 46 suites; 260 web tests passed with 2 optional skips.
- 11 installer fixtures; branding/delivery checks passed.
- Mac public downloaded archive: all 2,808 manifest entries, fresh install,
  repeated install retaining synthetic recordings/settings, relocated embedded
  Python importing the actual server and valid ad-hoc/helper signatures passed.
  This acceptance did not launch Capture or alter the owner's running install.
- [Application CI](https://github.com/AIAgentLbs/meeting-copilot-private-copy/actions/runs/39310615951)
  passed at the exact installer-pin revision.
- [Windows native build/test](https://github.com/AIAgentLbs/amanu-private-copy/actions/runs/39309225836)
  passed at the exact native revision.
- [Exact Windows package acceptance](https://github.com/AIAgentLbs/meeting-copilot-private-copy/actions/runs/39310615561)
  passed: 1,728 manifest hashes, fresh/repeat installation, synthetic recording
  preservation, five fixtures, PowerShell syntax, native metadata and embedded
  server self-test. Public ZIP bytes equal the accepted artifact.
- Live public feed selected 0.1.10 independently for macOS and Windows technical
  beta channels. The owner's running Mac 0.1.9 service returned `notify: true`,
  latest 0.1.10, release notes and no checker error without restarting Capture.

## Installer entry-point correction

The initial website guide incorrectly requested a second terminal command. The
distribution installer now waits for a successful, correctly identified local
health endpoint before opening the browser itself. A bounded readiness failure
reports the log/recovery path rather than opening an unrelated or broken page.
This installer-only correction keeps the immutable 0.1.10 archives unchanged.
Both startup success-after-delay and wrong-service/timeout paths were reproduced
as failing tests before the correction, then passed with the full installer suite.
The shipped native app already exposes Open MeetOnTrack assistant at the top of
the recorder window and in its menu, and setup completion opens the assistant.
The installed Mac button was clicked and opened the local assistant in Mike's
Chrome without a terminal command or Capture restart. Browser screenshots stay
outside Git. No native production-code change/replacement was needed.

## Explicit limits

Physical Windows host unavailable at final verification: no real microphone,
system-audio, headphones/reconnect, permissions or installed tray acceptance is
claimed. Clean-Mac permission/device acceptance also remains open. Mac is ad-hoc
signed/not notarized; Windows unsigned. Keep OS security protections enabled.
Optional own-client OAuth consent, real SMTP delivery, Telegram test sends and
local Office/PDF extraction remain the separately tracked work in `docs/TODO.md`.
No automatic installer is enabled; current scope is update notices/release notes
and a copyable user-triggered command. Never restart an active recording to update.
