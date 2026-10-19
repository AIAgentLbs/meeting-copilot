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
STARTTLS, an explicit username, sender and a provider-supported password or app
password. New installations suggest SMTP in the form without enabling email;
existing Gmail configurations retain their provider. Passwords are stored in
macOS Keychain or user-bound Windows DPAPI, never delivery.json, browser storage,
logs or Git. “Check SMTP” tests an in-memory draft without saving consent,
routing or credentials, and without sending a message. Save is explicit.

Google uses the user's imported Desktop OAuth client and an explicitly verified
account. Existing selected, identity-checked `gws-personal` and `gws-work` profiles
remain supported separately; new users do not need either CLI or a profile registry.
There is no ambient `gws`/`gog` fallback. Disconnect removes MeetOnTrack's local
OAuth tokens (retaining the client for reconnect), or detaches a legacy profile
without logging other applications out. It does not revoke the grant at Google;
users can also remove it in their Google account. Selecting another account disables its
delivery channels; explicitly saving enabled channels grants delivery consent.
Connection checks preserve unsaved form fields.

**Owner decision, 2026-10-19:** do not create a shared MeetOnTrack Google Cloud
project or OAuth application. Google is optional bring-your-own configuration:
each user owns their project, OAuth client and account authorization. SMTP does
not require Google Cloud. Local reports are the default, not a degraded mode.

### SMTP setup

1. Open Settings → Report storage and delivery; choose SMTP.
2. Enter the server, port and TLS/STARTTLS mode from your mail provider, your
   username, sender address and SMTP password or app password.
3. Check SMTP without sending email. This does not save credentials or opt in.
4. Enter the report recipient, enable automatic email and save. Leave the email
   toggle off to keep reports local. Drive is not required for PDF attachments.

For Gmail SMTP, an app password requires 2-Step Verification and may be unavailable
because of account/security policies; a normal Google password is not a universal
alternative. See [Google's app-password instructions](https://support.google.com/accounts/answer/185833).

### Own Google OAuth client (advanced, optional)

1. Create/select your own Google Cloud project. Enable Gmail API for email,
   Drive API for report storage, and Calendar/Docs/Sheets APIs if using those
   context sources. Configure the OAuth consent screen and add your account as
   a test user if the app is in Testing.
2. Create an OAuth client with application type **Desktop app** and download its
   JSON. Web clients and service-account JSON are rejected.
3. In Settings → Report storage and delivery → Google, choose the JSON file and
   click **Import my OAuth JSON**. Maximum size: 16 KB. Import selects the own-client
   connection and disables existing Google delivery until explicitly enabled again.
4. Enter the Google email to connect. Select sending, Drive storage and/or context
   reading permissions; click **Connect Google**. Complete consent in your browser,
   selecting that exact account, then click **Check account** in MeetOnTrack.
5. Separately enable email/Drive delivery and save, or connect context search and
   choose Calendar/Gmail/Drive sources. Authorization alone enables none of these.
6. To change grants, connect again with the desired permission selection. To switch
   accounts or replace an authorized client, disconnect first. SMTP stays independent.

An ordinary API key cannot authorize access to a private mailbox or Drive.
See [Google's desktop OAuth instructions](https://developers.google.com/identity/protocols/oauth2/native-app).
Do not send credentials to the developer or commit them to Git.

Client secrets and refresh tokens use macOS Keychain / user-bound Windows DPAPI,
not a plaintext client file. The user's downloaded original remains their own
file; MeetOnTrack does not delete it. Sign-in uses a temporary IPv4 loopback listener,
state validation and PKCE; it expires after five minutes. Token exchange and
refresh go directly to Google. Wrong-account authorization is rejected. Delivery
and context use separate explicit permission groups and never fall back to an
ambient developer account. Read-only context responses are bounded to 2 MiB and
cached only in memory; changing sources clears cached results.

Choosing report storage requests Google's full Drive scope, because the user may
choose an existing destination folder. The UI states that permission explicitly;
the app's delivery adapter exposes only file listing, creation and update, not
deletion. See [Drive scopes](https://developers.google.com/drive/api/guides/api-specific-auth).
External apps left in Google's Testing status normally receive seven-day refresh
tokens for these scopes; reconnect when expired. See [Google token expiration](https://developers.google.com/identity/protocols/oauth2#expiration).

**Acceptance boundary:** the native client, protected-store integration, real
loopback listener, PKCE generation, adapters and rejection paths have automated
coverage. The browser settings and real local import endpoint were checked with
synthetic credentials. This is not evidence of successful Google consent on a
new real account or acceptance on a clean Windows machine. Those remain release gates.

## Manual retry

Open Meetings → select a meeting → Report → Retry email delivery (or the Drive
or Telegram equivalent). Only the selected channel runs. A finished, processed
meeting, an existing PDF and an enabled channel are required. Repeating a sent or
uncertain request requires confirmation. A durable request ID prevents browser
retries from duplicating a request; uncertainty is written before dispatch.
Provider acknowledgements survive report regeneration in a separate local
delivery-receipts.json file. Uncertain email and Telegram outcomes are not
auto-retried. A Telegram timeout or malformed acknowledgement is not reported
as rejection: it requires an explicit retry with confirmation.

Newly enabled channels do not automatically backfill old meetings. Their reports
can be sent explicitly from the library. Automatic retries retain the existing
recent-report window. Existing Telegram setup is toggled here; this patch does
not add new Telegram account onboarding. Telegram sends the local PDF even if
Drive is disabled or unavailable. It uses the same Python as the server, with
hash-locked pure-Python dependencies bundled by both platform packagers.
`telegram_delivery.py --check --config <path> --account <label>` verifies existing
authorization without sending a message or initiating a login.

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
node scripts/test-delivery-ui.cjs
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
of either. Additional reproducible native/protocol acceptance:

```sh
python3 scripts/check-delivery-credentials.py
uv run --no-project --python 3.12 --with aiosmtpd==1.4.6 \
  python scripts/check-smtp-transport.py
```

On 2026-10-19 macOS Keychain passed create/read/update/delete using a separate
disposable item; production SMTP credentials were untouched. Real loopback
SMTP passed TLS and STARTTLS, authentication, PDF transport, no-send draft
checks and bad-password rejection. This exercises actual sockets, not a mocked
SMTP client, but does not prove delivery through an external mail provider.
Existing Telegram authorization was checked live without sending a message.
The native own-client JSON also passed import/reload/disconnect/forget against a
separate real macOS Keychain item; no live Google consent was involved. A runtime
check exposed settings reads waiting behind the archive's delivery network lock;
read snapshots now avoid that lock, with a concurrent slow-delivery regression.
Legacy Google login attempts expire after five minutes and disconnect reaps the
child process. Native own-client login closes its listener and session after
completion, cancellation, denial or timeout. To test actual library PKCE without
contacting Google, run the suite with `PYTHONPATH` set to the `_vendor` directory
produced by `scripts/vendor-delivery.py`; otherwise that dependency test skips.

OAuth protocol claims above were checked against Google primary documentation
and one independent Gemini-family pass on 2026-10-19; this was not a three-model
consensus. Security and runtime assertions come from source/tests, not model votes.

Notification polling is not automatic update installation; see
[UPDATES.md](UPDATES.md) for the separate release blocker.
