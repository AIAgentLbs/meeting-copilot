#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="${1:-$ROOT/capture/.build/MeetingCopilotCapture.app}"
OUT="${2:-$ROOT/dist/meeting-copilot-macos.zip}"
[[ -d "$APP" ]] || { echo "Missing app: $APP" >&2; exit 1; }
stage="$(mktemp -d "${TMPDIR:-/tmp}/meeting-copilot-release.XXXXXX")"
trap 'rm -rf "$stage"' EXIT
cp -R "$APP" "$stage/Meeting Copilot Capture.app"
mkdir -p "$stage/payload"
cp -R "$ROOT/copilot/web" "$stage/payload/web"
cp -R "$ROOT/copilot/bin" "$stage/payload/bin"
cp -R "$ROOT/copilot/config" "$stage/payload/config"
find "$stage" -name '__pycache__' -type d -prune -exec rm -rf {} +
mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
(cd "$stage" && /usr/bin/zip -qry "$OUT" .)
echo "$OUT"

