#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="${1:-$ROOT/capture/.build/MeetingCopilotCapture.app}"
OUT="${2:-$ROOT/dist/meeting-copilot-macos.zip}"
PYTHON_RUNTIME="${MEETING_COPILOT_PYTHON_RUNTIME:-}"
[[ -d "$APP" ]] || { echo "Missing app: $APP" >&2; exit 1; }
[[ -x "$PYTHON_RUNTIME/bin/python3" ]] || { echo 'Set MEETING_COPILOT_PYTHON_RUNTIME to a clean relocatable arm64 Python distribution' >&2; exit 1; }
"$PYTHON_RUNTIME/bin/python3" -I -c 'import platform, sys; assert platform.machine() == "arm64" and sys.version_info >= (3, 10)'
stage="$(mktemp -d "${TMPDIR:-/tmp}/meeting-copilot-release.XXXXXX")"
trap 'rm -rf "$stage"' EXIT
cp -R "$APP" "$stage/Meeting Copilot Capture.app"
mkdir -p "$stage/payload"
cp -R "$PYTHON_RUNTIME" "$stage/payload/python"
cp -R "$ROOT/copilot/web" "$stage/payload/web"
cp -R "$ROOT/copilot/bin" "$stage/payload/bin"
swiftc "$ROOT/copilot/bin/ZoomWindowFinder.swift" -o "$stage/payload/bin/zoom-window-finder"
swiftc "$ROOT/copilot/bin/ZoomFrameInspector.swift" -o "$stage/payload/bin/zoom-frame-inspector"
swiftc "$ROOT/copilot/bin/DetectSpeechLanguage.swift" -o "$stage/payload/bin/detect-speech-language"
for helper in zoom-window-finder zoom-frame-inspector detect-speech-language; do
  codesign --force --sign - --timestamp=none "$stage/payload/bin/$helper"
done
cp -R "$ROOT/copilot/config" "$stage/payload/config"
find "$stage" -name '__pycache__' -type d -prune -exec rm -rf {} +
python3 - "$stage" "$(git -C "$ROOT" rev-parse HEAD)" <<'PY'
import hashlib, json, os, pathlib, plistlib, sys
root = pathlib.Path(sys.argv[1])
info = plistlib.loads((root / "Meeting Copilot Capture.app/Contents/Info.plist").read_bytes())
files = {}
for path in sorted(root.rglob("*")):
    if path.is_symlink():
        # zip -y stores the link itself, not the bytes it points to. Include
        # framework directory links as well as links to regular files.
        files[str(path.relative_to(root))] = hashlib.sha256(os.readlink(path).encode()).hexdigest()
        continue
    if path.is_file():
        relative = str(path.relative_to(root))
        if path.suffix in {".caf", ".wav", ".log"} or path.name in {"meeting.json", "report.json", "delivery.json", "frames.json", "repos.json", "active-repos.json"}:
            raise SystemExit(f"Private runtime data must not enter a release: {relative}")
        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
manifest = {"version": info["CFBundleShortVersionString"], "source_revision": sys.argv[2],
            "architecture": "arm64", "channel": "technical-beta", "notarized": False,
            "automatic_updates": bool(info.get("SUEnableAutomaticChecks", False)), "sha256": files}
(root / "release.json").write_text(json.dumps(manifest, indent=2) + "\n")
PY
mkdir -p "$(dirname "$OUT")"
[[ ! -e "$OUT" ]] || { echo "Refusing to overwrite an existing release: $OUT" >&2; exit 1; }
(cd "$stage" && /usr/bin/zip -qry "$OUT" .)
echo "$OUT"
