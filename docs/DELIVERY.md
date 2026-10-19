# Report storage and delivery

Settings → Report storage and delivery controls email, Google Drive and the
existing Telegram connection independently. New installations are local-only;
existing explicitly configured destinations retain their previous behavior.
Connecting an account does not enable delivery. Context-search permissions are
separate from report delivery. Disabling a channel stops future sends and pending
retries, not a request already accepted by its provider.

## Email and Google

Email can use Gmail or SMTP. The recipient is separate from the sender account;
the report PDF is attached, so Drive is not required. SMTP requires TLS or
STARTTLS, an explicit username, sender and app password. Passwords are stored in
macOS Keychain or user-bound Windows DPAPI, never delivery.json, browser storage,
logs or Git. “Check SMTP” tests an in-memory draft without saving consent,
routing or credentials, and without sending a message. Save is explicit.

Google uses the selected, identity-checked `gws-personal` or `gws-work` profile.
There is no ambient `gws`/`gog` fallback. Disconnect affects MeetOnTrack, not other
applications sharing the profile. Selecting another account alone disables its
delivery channels; explicitly saving enabled channels grants delivery consent.
Connection checks preserve unsaved form fields.

**Public onboarding limitation:** named wrappers and their OAuth client/profile
registry must already exist. This patch does not ship a public Google OAuth
application or provision a new customer's profile. Missing setup is reported
explicitly; local storage and SMTP remain usable. Do not advertise universal
one-click Google onboarding until a clean-machine flow is implemented and tested.

## Manual retry

Open Meetings → select a meeting → Report → Retry email delivery (or the Drive
or Telegram equivalent). Only the selected channel runs. A finished, processed
meeting, an existing PDF and an enabled channel are required. Repeating a sent or
uncertain request requires confirmation. A durable request ID prevents browser
retries from duplicating a request; uncertainty is written before dispatch.
Provider acknowledgements survive report regeneration in a separate local
delivery-receipts.json file. Uncertain email outcomes are not auto-retried.

Newly enabled channels do not automatically backfill old meetings. Their reports
can be sent explicitly from the library. Automatic retries retain the existing
recent-report window. Existing Telegram setup is toggled here; this patch does
not add new Telegram account onboarding.

## Attachment regression

The Google CLI rejects an attachment or upload outside its process working
directory. Each attachment/upload invocation now runs with its file's parent as
the subprocess-local cwd. It does not change the multithreaded server's cwd.
Persisted diagnostics contain allowlisted reason codes, not raw CLI output.

## Verification

Run the synthetic Python suite from the repository:

```sh
uv run --no-project --python 3.12 --with pillow==11.3.0 --with numpy==2.3.3 \
  python -m unittest discover -s copilot/web -p 'test_*.py'
node --check copilot/web/delivery.js
node --check copilot/web/app.js
```

The isolated preview can exercise real UI/API validation with a stubbed provider:

```sh
python3 scripts/preview-first-run.py --port 43992 --delivery-fixture
```

It uses disposable synthetic state and never sends a real report. Regression
coverage includes disabled channels, account changes, no backfill, attachment
cwd, durable receipts, explicit resend confirmation, repeated request IDs, draft
SMTP checks and credential non-disclosure. Live SMTP and Windows DPAPI acceptance
require an actual configured test account and Windows host; mocks are not proof
of either. Notification polling is not automatic update installation; see
[UPDATES.md](UPDATES.md) for the separate release blocker.
