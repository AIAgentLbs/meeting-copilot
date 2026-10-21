#!/bin/bash
set -euo pipefail

REPO="AIAgentLbs/meetontrack"
VERSION="v0.1.12"
ASSET="meeting-copilot-macos.zip"
SHA256="1a6bf0a3f25734376c2a87db2430be3f36144d15e2bac31db74828ab515a0fea"
SHARE="${MEETING_COPILOT_SHARE_ROOT:-$HOME/.local/share/meeting-copilot}"
CONFIG="${MEETING_COPILOT_CONFIG_ROOT:-$HOME/.config/meeting-copilot}"
BIN="${MEETING_COPILOT_BIN_ROOT:-$HOME/.local/bin}"
AGENTS="${MEETING_COPILOT_AGENTS_ROOT:-$HOME/Library/LaunchAgents}"
LABEL="com.aiagentlbs.meeting-copilot"

say() { printf 'MeetOnTrack · %s\n' "$*"; }
fail() { printf 'MeetOnTrack · ERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || fail "macOS is required"
[[ "$(uname -m)" == "arm64" ]] || fail "this beta currently requires Apple Silicon"
os_version="$(sw_vers -productVersion)"
[[ "${os_version%%.*}" -ge 15 ]] || fail "macOS 15 or later is required"
for tool in curl unzip shasum pgrep; do
  command -v "$tool" >/dev/null || fail "$tool is required; see https://meetontrack.com/ru/#install"
done
# Recording and local transcription do not require a paid AI subscription.
# The assistant's optional connection is checked explicitly in first-run UI.

require_capture_closed() {
  if pgrep -f '/MeetingCopilotCapture([[:space:]]|$)' >/dev/null 2>&1; then
    fail "Quit Meeting Copilot Capture after your call before installing. The running capture was not stopped."
  fi
}
require_capture_closed

tmp="$(mktemp -d "${TMPDIR:-/tmp}/meeting-copilot.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
url="${MEETING_COPILOT_ASSET_URL:-https://github.com/$REPO/releases/download/$VERSION/$ASSET}"
expected="${MEETING_COPILOT_ASSET_SHA256:-$SHA256}"
if [[ -n "${MEETING_COPILOT_ASSET_URL:-}" && -z "${MEETING_COPILOT_ASSET_SHA256:-}" ]]; then
  fail "An alternate asset URL requires MEETING_COPILOT_ASSET_SHA256"
fi
[[ "$expected" =~ ^[a-fA-F0-9]{64}$ ]] || fail "Invalid expected SHA-256"
say "downloading $VERSION"
curl --fail --location --silent --show-error --connect-timeout 15 --max-time 300 "$url" -o "$tmp/$ASSET"
actual="$(shasum -a 256 "$tmp/$ASSET")"
[[ "${actual%% *}" == "$expected" ]] || fail "Release checksum mismatch; nothing was installed"
unzip -tq "$tmp/$ASSET" >/dev/null || fail "Release archive is damaged"
unzip -q "$tmp/$ASSET" -d "$tmp/release"
[[ -d "$tmp/release/Meeting Copilot Capture.app" ]] || fail "release app is missing"
[[ -d "$tmp/release/payload/web" ]] || fail "release payload is missing"
for file in release.json payload/web/server.py payload/bin/meeting-copilot payload/config/refresh-repos.py payload/config/SESSION.md payload/config/delivery.json.example; do
  [[ -f "$tmp/release/$file" ]] || fail "Release file is missing: $file"
done
python="$tmp/release/payload/python/bin/python3"
[[ -x "$python" ]] || fail "Release Python runtime is missing"
"$python" -I -c 'import ssl, sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || fail "Packaged Python runtime cannot start"

# Prepare everything before touching an existing installation.
mkdir -p "$tmp/helpers"
for helper in zoom-window-finder zoom-frame-inspector detect-speech-language; do
  [[ -x "$tmp/release/payload/bin/$helper" ]] || fail "Release helper is missing: $helper"
  install -m 0755 "$tmp/release/payload/bin/$helper" "$tmp/helpers/$helper"
done
require_capture_closed
backup_stamp="$(date +%Y%m%d-%H%M%S)-$$"

app_root="${MEETING_COPILOT_APP_ROOT:-/Applications}"
if [[ ! -w "$app_root" ]]; then
  app_root="$HOME/Applications"
  mkdir -p "$app_root"
fi
app="$app_root/Meeting Copilot Capture.app"
if [[ -e "$app" ]]; then
  backup="$app_root/Meeting Copilot Capture.backup-$backup_stamp.app"
  mv "$app" "$backup"
  say "previous app preserved at $backup"
fi
cp -R "$tmp/release/Meeting Copilot Capture.app" "$app"

mkdir -p "$SHARE" "$CONFIG" "$BIN" "$AGENTS" "$SHARE/bin"
[[ ! -e "$SHARE/python" ]] || mv "$SHARE/python" "$SHARE/python.backup-$backup_stamp"
cp -R "$tmp/release/payload/python" "$SHARE/python"
python="$SHARE/python/bin/python3"
for dir in web; do
  [[ ! -e "$SHARE/$dir" ]] || mv "$SHARE/$dir" "$SHARE/$dir.backup-$backup_stamp"
  cp -R "$tmp/release/payload/$dir" "$SHARE/$dir"
done
install -m 0644 "$tmp/release/release.json" "$SHARE/release.json"
install -m 0755 "$tmp/release/payload/bin/meeting-copilot" "$BIN/meeting-copilot"
install -m 0755 "$tmp/release/payload/config/refresh-repos.py" "$CONFIG/refresh-repos.py"
# One-time removal of retired usage-reporting state; preserve all other settings.
"$python" - "$CONFIG" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
config = root / "config.json"
if config.is_file():
    value = json.loads(config.read_text())
    if "analytics" in value:
        del value["analytics"]
        temporary = config.with_name("config.json.statistics-removal.tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        temporary.chmod(0o600)
        temporary.replace(config)
for name in ("analytics.json", "analytics-pending.json"):
    (root / name).unlink(missing_ok=True)
PY
[[ -f "$CONFIG/SESSION.md" ]] || install -m 0644 "$tmp/release/payload/config/SESSION.md" "$CONFIG/SESSION.md"
[[ -f "$CONFIG/delivery.json.example" ]] || install -m 0600 "$tmp/release/payload/config/delivery.json.example" "$CONFIG/delivery.json.example"

install -m 0755 "$tmp/helpers/zoom-window-finder" "$SHARE/bin/zoom-window-finder"
install -m 0755 "$tmp/helpers/zoom-frame-inspector" "$SHARE/bin/zoom-frame-inspector"
install -m 0755 "$tmp/helpers/detect-speech-language" "$SHARE/bin/detect-speech-language"

# Discovery is explicit (meeting-copilot --refresh). A first install must not
# scan unrelated project directories or write to a different user's config.
if [[ ! -f "$CONFIG/repos.json" ]]; then
  "$python" - "$CONFIG/repos.json" <<'PY'
import json, pathlib, sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"repositories": [], "repository_count": 0, "search_roots": []}) + "\n")
PY
fi
if [[ ! -f "$CONFIG/active-repos.json" ]]; then
  "$python" - "$CONFIG/repos.json" "$CONFIG/active-repos.json" <<'PY'
import json, pathlib, sys
source, target = map(pathlib.Path, sys.argv[1:])
data = json.loads(source.read_text())
data["repositories"] = []
data["repository_count"] = 0
target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
PY
fi

"$python" - "$AGENTS/$LABEL.plist" "$SHARE" "$BIN" "$LABEL" <<'PY'
import pathlib, plistlib, sys
target, share, bin_root, label = sys.argv[1:]
value = {
    "Label": label,
    "ProgramArguments": [sys.executable, str(pathlib.Path(share)/"web/server.py"), "--port", "43121", "--no-open"],
    "RunAtLoad": True, "KeepAlive": True, "ProcessType": "Interactive",
    "EnvironmentVariables": {"PATH": f"/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:{bin_root}"},
    "StandardOutPath": str(pathlib.Path(share)/"web/server.log"),
    "StandardErrorPath": str(pathlib.Path(share)/"web/server.log"),
}
with pathlib.Path(target).open("wb") as handle:
    plistlib.dump(value, handle)
PY

if [[ "${MEETING_COPILOT_SKIP_LAUNCH:-0}" != "1" ]]; then
  # bootout can return before launchd has removed the old job; bootstrapping the
  # same label then fails with "5: Input/output error" (0.1.9 -> 0.1.11 upgrade).
  # Wait until the job is gone, and retry a bounded number of times.
  domain="gui/$(id -u)"
  bootstrapped=false
  for attempt in 1 2 3; do
    launchctl bootout "$domain/$LABEL" >/dev/null 2>&1 || true
    for wait in {1..40}; do
      launchctl print "$domain/$LABEL" >/dev/null 2>&1 || break
      sleep 0.25
    done
    if bootstrap_error="$(launchctl bootstrap "$domain" "$AGENTS/$LABEL.plist" 2>&1)"; then
      bootstrapped=true
      break
    fi
    sleep 1
  done
  [[ "$bootstrapped" == true ]] || fail "Files installed, but macOS could not start the local assistant service ($bootstrap_error). Rerun the installer."
  open "$app"
  # A successful bootstrap is not yet an HTTP-ready assistant. Do not open a
  # broken browser tab or require a second terminal command from a new user.
  ready=false
  for attempt in {1..40}; do
    if curl --fail --silent --connect-timeout 1 --max-time 1 \
      "http://127.0.0.1:43121/api/health" \
      | "$python" -I -c 'import json,sys; value=json.load(sys.stdin); sys.exit(0 if value.get("ok") is True and value.get("service")=="meeting-copilot" else 1)' \
        >/dev/null 2>&1; then
      ready=true
      break
    fi
    sleep 0.25
  done
  [[ "$ready" == true ]] || fail "Files installed, but the local assistant did not become ready. Reopen MeetOnTrack or rerun the installer. Log: $SHARE/web/server.log"
  open "http://127.0.0.1:43121/" || fail "The assistant is running, but macOS could not open the browser. Use Open MeetOnTrack assistant in the app."
  say "the assistant is open in your browser; finish first-run permissions and model setup in MeetOnTrack"
fi
say "$VERSION installed; existing recordings and private settings were preserved"
say "reopen anytime with Open MeetOnTrack assistant in the app window or menu bar"
