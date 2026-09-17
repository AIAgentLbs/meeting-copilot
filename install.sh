#!/bin/bash
set -euo pipefail

REPO="AIAgentLbs/meeting-copilot"
ASSET="meeting-copilot-macos.zip"
SHARE="$HOME/.local/share/meeting-copilot"
CONFIG="$HOME/.config/meeting-copilot"
BIN="$HOME/.local/bin"
AGENTS="$HOME/Library/LaunchAgents"
LABEL="com.aiagentlbs.meeting-copilot"

say() { printf 'Meeting Copilot · %s\n' "$*"; }
fail() { printf 'Meeting Copilot · ERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || fail "macOS is required"
[[ "$(uname -m)" == "arm64" ]] || fail "this beta currently requires Apple Silicon"
command -v curl >/dev/null || fail "curl is required"
command -v unzip >/dev/null || fail "unzip is required"
command -v python3 >/dev/null || fail "Python 3 is required"
command -v codex >/dev/null || fail "Codex CLI is required: https://developers.openai.com/codex/cli"

tmp="$(mktemp -d "${TMPDIR:-/tmp}/meeting-copilot.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
url="${MEETING_COPILOT_ASSET_URL:-https://github.com/$REPO/releases/latest/download/$ASSET}"
say "downloading the current signed package"
curl --fail --location --silent --show-error "$url" -o "$tmp/$ASSET"
unzip -q "$tmp/$ASSET" -d "$tmp/release"
[[ -d "$tmp/release/Meeting Copilot Capture.app" ]] || fail "release app is missing"
[[ -d "$tmp/release/payload/web" ]] || fail "release payload is missing"

app_root="${MEETING_COPILOT_APP_ROOT:-/Applications}"
if [[ ! -w "$app_root" ]]; then
  app_root="$HOME/Applications"
  mkdir -p "$app_root"
fi
app="$app_root/Meeting Copilot Capture.app"
if [[ -e "$app" ]]; then
  backup="$app_root/Meeting Copilot Capture.backup-$(date +%Y%m%d-%H%M%S).app"
  mv "$app" "$backup"
  say "previous app preserved at $backup"
fi
cp -R "$tmp/release/Meeting Copilot Capture.app" "$app"

mkdir -p "$SHARE" "$CONFIG" "$BIN" "$AGENTS" "$SHARE/bin"
for dir in web; do
  [[ ! -e "$SHARE/$dir" ]] || mv "$SHARE/$dir" "$SHARE/$dir.backup-$(date +%Y%m%d-%H%M%S)"
  cp -R "$tmp/release/payload/$dir" "$SHARE/$dir"
done
install -m 0755 "$tmp/release/payload/bin/meeting-copilot" "$BIN/meeting-copilot"
install -m 0755 "$tmp/release/payload/config/refresh-repos.py" "$CONFIG/refresh-repos.py"
[[ -f "$CONFIG/SESSION.md" ]] || install -m 0644 "$tmp/release/payload/config/SESSION.md" "$CONFIG/SESSION.md"
[[ -f "$CONFIG/delivery.json.example" ]] || install -m 0600 "$tmp/release/payload/config/delivery.json.example" "$CONFIG/delivery.json.example"

swiftc "$tmp/release/payload/bin/ZoomWindowFinder.swift" -o "$SHARE/bin/zoom-window-finder"
swiftc "$tmp/release/payload/bin/ZoomFrameInspector.swift" -o "$SHARE/bin/zoom-frame-inspector"

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

python_bin="$(command -v python3)"
cat > "$AGENTS/$LABEL.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$LABEL</string>
<key>ProgramArguments</key><array><string>$python_bin</string><string>$SHARE/web/server.py</string><string>--port</string><string>43121</string><string>--no-open</string></array>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
<key>ProcessType</key><string>Interactive</string>
<key>StandardOutPath</key><string>$SHARE/web/server.log</string>
<key>StandardErrorPath</key><string>$SHARE/web/server.log</string>
</dict></plist>
PLIST

if [[ "${MEETING_COPILOT_SKIP_LAUNCH:-0}" != "1" ]]; then
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$AGENTS/$LABEL.plist"
  open "$app"
fi
say "installed"
say "run: meeting-copilot"
say "if the command is not found, add $BIN to PATH or run $BIN/meeting-copilot"
