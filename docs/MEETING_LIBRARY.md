# Meeting library

Approved behavior: the library is the default view outside a call. During capture
it is hidden by default and available through **Meetings** as a non-modal drawer.
Manually opened history is not dismissed by polling. Closing it does not reopen
it on the next poll. A real transition to a completed call returns to the library.

Browsing never binds the live AI session to an archived meeting, resets a call,
changes recording, submits an analysis request, or clears an unsent note. Browser
request generations prevent late archive/search responses from replacing a newer
selection or reopening closed history. Labels, drafts, and DOM state stay separate.

## Finding and reading meetings

- Local search covers titles, transcript speaker names and text, journal notes,
  meeting chat, and stored participant names. It runs on demand with debounce,
  not during every live-state poll. Only compact list metadata is returned.
- Recording metadata and journal indexes are reused within one operation, never
  cached indefinitely. Transcripts are processed one at a time during a search.
- State labels distinguish recording, capture warnings, report/analysis/transcript
  availability, and the absence of recognized speech. Missing text is not a claim
  that an original recording contained no speech.
- Overview points come from existing facts/decisions/commitments. Open questions
  exclude resolved items. Short/sparse material receives a quality warning.
- User titles live in `archive/<id>/library.json`, not original meeting JSON/audio.
  Continuous-call grouping and automatic report source signatures use the original
  source title, so a library rename cannot trigger automatic report re-delivery.
- Copy summary/dialogue, rename, open audio/folder, and existing report actions are
  available from the selected meeting. Local opening resolves paths inside known
  storage roots and restricts file types; it never runs a supplied shell command.

## Explicit summary revisions

The correction field updates only the selected completed meeting's overview.
It does not modify PDFs, delivered reports, global preferences, or live assistant
state. There is no background AI call when merely browsing a meeting.

The worker uses a separate session of the AI tool, model, effort and speed chosen
for summary rewrites in Getting started (Codex, Claude Code or a local Ollama).
Without a usable choice the rewrite does not run and the previous result is kept.
The call starts in an empty working directory with no repositories: Codex runs
with a read-only permissions profile, approval `never` and its tools disabled;
Claude Code runs restricted with no tools, no user settings and no MCP servers;
Ollama receives only the prompt. It reuses the chosen tool's existing sign-in, so
a cloud account's own policies still apply. It is not an API-only strict
single-purpose inference boundary; the UI discloses this.

The prompt contains bounded selected-meeting material and the current overview.
One job runs at a time. At commit, the meeting must still be completed and its
source signature unchanged. Results preserve manual titles and record model,
source signature and timestamp locally. Failure retains the previous result.

## Verification

```sh
python3 -m unittest discover -s copilot/web -p 'test_*.py'
PLAYWRIGHT_MODULE=/path/to/playwright node scripts/test-library-ui.cjs
```

Optional authenticated smoke, synthetic meeting text only. Point it at a
`config.json` whose `ai.purposes.summary_rewrite` is set:

```sh
cd copilot/web
MEETONTRACK_AI_SMOKE_CONFIG=/path/to/config.json python3 -m unittest test_summary_rewrite.SummaryRewriteTests.test_authenticated_provider_can_rewrite_synthetic_meeting
```

Browser fixtures verify desktop/mobile layout and controls, not physical iPhone
or Android touch behavior. Actual meeting text never belongs in Git fixtures.
