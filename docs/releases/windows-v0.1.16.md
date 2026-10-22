# MeetOnTrack 0.1.16 for Windows

Technical beta for Windows 11 24H2+, x64. Capture, .NET, Python and the web UI
are included; no compiler or SDK is required. Initial setup downloads local
speech models. AI answers are optional and use an AI tool you already have.

- Fact check is the fourth column of Call overview, next to the questions and
  risks, instead of a strip above the tabs. During a call, statements that can
  be checked appear there with the name of the person who said them: green
  "Confirmed", yellow "Neither confirmed nor refuted", or red "Refuted" with
  the source and what is actually true. The check uses the AI you chose in
  Getting started. It checks on the web only when that AI can search the web;
  otherwise it checks your connected knowledge base and says which AI would
  add web checks. Finished checks also appear in the meeting report.
- Chat shows only your questions, your notes and MeetOnTrack's answers. The
  automatic analysis of the call no longer appears there, also in older
  meetings; it goes to Call overview. The separate Meeting chat tab is gone.
  Questions people write in the call's own text chat still reach Call
  overview.
- Open, Needs clarification and Closed in Call overview are filters: click one
  to show or hide those items. Your choice is remembered.
- Links and services shows one card per link. Links to the call itself (Zoom,
  Google Meet, Microsoft Teams, Telemost and similar) are no longer added.
  Older meetings show the cleaned list too.
- A cleaner main screen: no title bar above the chat, no label above the input
  and no hint under it. Show transcript is in the top bar. The assistant is
  called MeetOnTrack: its answers are signed MeetOnTrack and the input says
  "Ask MeetOnTrack or capture a thought during the conversation." ("Спросите
  MeetOnTrack или запишите мысль по ходу разговора." in Russian).
- The PDF report is branded MeetOnTrack.
- A call followed right away by another now gets its final transcript and its
  report. Before, the finished call kept only its live text and could be left
  without a report.
- On the first start after the update, older meetings are brought up to date.
  Meetings that ended within the last 3 days get their reports sent
  automatically through the delivery you set up. Older meetings get a saved
  report with a Send button, so nothing old is sent without you.

Everything from 0.1.15 is included. The plain explanation of sound dropouts in
the library is part of the Mac release; the Windows recorder does not report
dropouts yet.

The speech recognition choice from the Mac release is not available on Windows
yet (MEETONTRACK-69). Getting started says so, and the Windows recorder keeps
transcribing with its local speech models as before.

Fact checking sends the checked statement and matching knowledge base excerpts
to the AI you chose.

Finish the call and close Capture before installing or updating:

```powershell
irm https://meetontrack.com/install.ps1 | iex
```

Version 0.1.10 and 0.1.11 do not show this update in the app: the project's
GitHub address changed, and those versions reject release pages at the new
address. Run the command above once. Version 0.1.12 and later check the new
address.

Recordings, model data and settings live outside the versioned app directory.
The installer verifies the package checksum. No automatic installer is enabled.

## Build identity

Application source: `55764ba7e05335f07b839ac2c5d61e6a91c743e2`.
Native source: `50e7448c880538ab96b57e093b4f7214a7a51de0`
([recorder run 39649348946](https://github.com/AIAgentLbs/meetontrack-recorder/actions/runs/39649348946)).
ZIP SHA-256: `d209149d6edad557ea10c03b5d2c81535e12897702a07821ccfcf86704f80942`.
The integrated package version is 0.1.16; its independently versioned native
component retains 0.6.6. The web update checker compares integrated versions.

## Limits

Unsigned technical beta; keep SmartScreen and antivirus enabled. Real-device
audio, permissions, headphone reconnects and installed tray acceptance are not
claimed for this release. Test a short call and inspect both sides before
relying on a long recording. Fact checks come from the AI you chose; open the
source before relying on a verdict. Local PDF/Office extraction and optional
screen OCR dependencies are not included. Speaker labels may need correction.
