#!/bin/bash
set -euo pipefail

REPO="AIAgentLbs/meeting-copilot"
VERSION="v0.1.7"
ASSET="meeting-copilot-macos.zip"
SHA256="fa3fedcf4fca053266732d6515bb5564eecb3c55b75aba6540a147b089b16b4a"
SHARE="${MEETING_COPILOT_SHARE_ROOT:-$HOME/.local/share/meeting-copilot}"
CONFIG="${MEETING_COPILOT_CONFIG_ROOT:-$HOME/.config/meeting-copilot}"
BIN="${MEETING_COPILOT_BIN_ROOT:-$HOME/.local/bin}"
AGENTS="${MEETING_COPILOT_AGENTS_ROOT:-$HOME/Library/LaunchAgents}"
LABEL="com.aiagentlbs.meeting-copilot"

say() { printf 'Meeting Copilot · %s\n' "$*"; }
fail() { printf 'Meeting Copilot · ERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || fail "macOS is required"
[[ "$(uname -m)" == "arm64" ]] || fail "this beta currently requires Apple Silicon"
os_version="$(sw_vers -productVersion)"
[[ "${os_version%%.*}" -ge 15 ]] || fail "macOS 15 or later is required"
for tool in curl unzip shasum python3 swiftc pgrep; do
  command -v "$tool" >/dev/null || fail "$tool is required; see https://aiagentlbs.github.io/meeting-copilot/ru/#install"
done
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || fail "Python 3.10 or later is required"
swiftc --version >/dev/null 2>&1 || fail "Apple Command Line Tools are required; run xcode-select --install, then try again"
command -v codex >/dev/null || fail "Codex CLI is required: https://developers.openai.com/codex/cli"
codex --version >/dev/null 2>&1 || fail "Codex CLI or its runtime is unavailable"

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
for file in payload/web/server.py payload/bin/meeting-copilot payload/config/refresh-repos.py payload/config/SESSION.md payload/config/delivery.json.example; do
  [[ -f "$tmp/release/$file" ]] || fail "Release file is missing: $file"
done

# Prepare everything before touching an existing installation.
mkdir -p "$tmp/helpers"
swiftc "$tmp/release/payload/bin/ZoomWindowFinder.swift" -o "$tmp/helpers/zoom-window-finder"
swiftc "$tmp/release/payload/bin/ZoomFrameInspector.swift" -o "$tmp/helpers/zoom-frame-inspector"
swiftc "$tmp/release/payload/bin/DetectSpeechLanguage.swift" -o "$tmp/helpers/detect-speech-language"
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
for dir in web; do
  [[ ! -e "$SHARE/$dir" ]] || mv "$SHARE/$dir" "$SHARE/$dir.backup-$backup_stamp"
  cp -R "$tmp/release/payload/$dir" "$SHARE/$dir"
done
install -m 0755 "$tmp/release/payload/bin/meeting-copilot" "$BIN/meeting-copilot"
install -m 0755 "$tmp/release/payload/config/refresh-repos.py" "$CONFIG/refresh-repos.py"
[[ -f "$CONFIG/SESSION.md" ]] || install -m 0644 "$tmp/release/payload/config/SESSION.md" "$CONFIG/SESSION.md"
[[ -f "$CONFIG/delivery.json.example" ]] || install -m 0600 "$tmp/release/payload/config/delivery.json.example" "$CONFIG/delivery.json.example"

install -m 0755 "$tmp/helpers/zoom-window-finder" "$SHARE/bin/zoom-window-finder"
install -m 0755 "$tmp/helpers/zoom-frame-inspector" "$SHARE/bin/zoom-frame-inspector"
install -m 0755 "$tmp/helpers/detect-speech-language" "$SHARE/bin/detect-speech-language"

python3 "$CONFIG/refresh-repos.py"
if [[ ! -f "$CONFIG/active-repos.json" ]]; then
  python3 - "$CONFIG/repos.json" "$CONFIG/active-repos.json" <<'PY'
import json, pathlib, sys
source, target = map(pathlib.Path, sys.argv[1:])
data = json.loads(source.read_text())
data["repositories"] = data.get("repositories", [])[:15]
data["repository_count"] = len(data["repositories"])
target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
PY
fi

python3 - "$AGENTS/$LABEL.plist" "$SHARE" "$BIN" "$LABEL" <<'PY'
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
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$AGENTS/$LABEL.plist"
  open "$app"
fi
say "$VERSION installed; existing recordings and private settings were preserved"
say "run: meeting-copilot"
say "if the command is not found, add $BIN to PATH or run $BIN/meeting-copilot"
