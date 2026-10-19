# Own-client Google setup and delivery acceptance — 2026-10-19

## Implemented and installed on the existing Mac

- User-owned Desktop OAuth JSON import in Settings, without a shared developer
  Cloud project, gws install or profile registry. Existing named profiles remain
  separate supported connections. No owner credentials are distributed.
- PKCE/state-protected temporary loopback login, expected-email validation,
  protected credential storage, token refresh, cancellation and disconnect.
- Independent grants for Gmail sending, Drive storage and read-only context;
  import/connect do not enable any automatic delivery or search.
- Existing SMTP, per-channel opt-in, PDF attachment without Drive, explicit retry
  confirmation and durable unknown-outcome handling remain intact.
- Bounded Google API adapter; allowlisted hosts, no redirects or automatic send
  replay, response-size limit and safe error codes.
- Both package builders vendor the hash-locked pure-Python Google/Telegram runtime.

## Evidence

- Python 3.12 with the vendored OAuth dependencies, Pillow and NumPy: **260 tests
  passed, one skipped**. Includes real loopback callback and real-library PKCE
  generation, rejected client/host/state/account/permissions, refresh failures,
  cancellation/timeout, no implicit consent and bounded/redacted responses.
- `node scripts/test-delivery-ui.cjs`: passed synthetic handler checks for JSON
  size/parsing/cleanup, permissions, unchanged delivery drafts, disconnect,
  provider-URL validation and no automatic sends.
- Real disposable HTTP server: rejected web-client JSON, accepted a synthetic
  Desktop client, returned no client secret and left delivery disabled.
- Mike's Chrome: inspected English and Russian settings and the imported-client
  controls using synthetic data. Real provider consent was not performed.
- `python3 scripts/check-delivery-credentials.py`: actual macOS Keychain
  create/read/update/delete and OAuth JSON import/reload/disconnect/forget passed
  with disposable items; production secrets were not touched.
- Deployment success/rollback/active-recording guard: three tests passed.
  Release-branding checks: three tests passed.
- Installed 11 matching web source files plus verified vendored dependencies.
  Web LaunchAgent remains running with KeepAlive and RunAtLoad. Capture was not
  restarted. Before/after Capture PID unchanged, report count remained 40 and
  delivery-settings checksum unchanged.
- The first live readback exposed settings waiting behind the archive's network
  delivery lock. Added a concurrency regression and removed that lock from read
  snapshots. Mutations retain account/consent serialization and return a bounded
  `delivery_busy` response instead of hanging behind an upload. Final installed
  settings response: **0.07 seconds**, versus requests
  timing out at 8–50 seconds before the correction.
- Recoverable operator backup:
  `~/.local/share/meeting-copilot/backups/20261019T182051Z-delivery-runtime`.
  This hotfix mechanism is not the end-user automatic updater.

## Branding boundary

Swift user-facing setup/settings/menu labels and Windows native UI source use
MeetOnTrack. Installed Mac display name is MeetOnTrack. Updated the Swift window
screenshot test to match the new title. Do not rename upstream namespaces,
compatibility identifiers, existing storage paths or remove legal attribution.
The unrelated pending native icon edit was not changed by this work.

## Still required before public release acceptance

- User-owned real Google consent and token lifecycle on clean Mac and Windows,
  authorized Gmail send/Drive upload and opt-in context search.
- External SMTP-provider send and actual Windows DPAPI acceptance. Loopback SMTP
  tests from this date are not external delivery evidence.
- Real Windows installed branding/icon, installer and runtime acceptance.
  Tailscale reports the host online, but the SSH host-key scan returned no key;
  no unverified host key was accepted and no remote install was claimed.
- Complete-product automatic update installation, signed manifests/packages,
  idle-call coordination, interruption/rollback and exact cross-version testing.
- A new public pair of tested packages. These local changes are not a published
  release. The complete remaining product backlog is [TODO.md](../TODO.md).

The Impeccable review kept optional Google setup separate from local/SMTP use
and permissions separate from activation. Its detector still flags pre-existing
small text/contrast/dialog spacing; those remain in the accessibility backlog.
