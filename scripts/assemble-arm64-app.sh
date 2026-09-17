#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CAPTURE="$ROOT/capture"
APP="$CAPTURE/.build/MeetingCopilotCapture.app"
DONOR="${MEETING_COPILOT_RUNTIME_DONOR:-/Applications/Meeting Copilot Capture.app}"
BIN="$CAPTURE/.build/arm64-apple-macosx/release/meetingcopilot"
SPARKLE="$(find "$CAPTURE/.build/artifacts/sparkle" -type d -name Sparkle.framework -path '*macos-arm64_x86_64*' | head -1)"
[[ -x "$BIN" ]] || { echo "Run swift build -c release first" >&2; exit 1; }
[[ -d "$DONOR" ]] || { echo "A LocalVQE runtime donor app is required" >&2; exit 1; }
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/Models" "$APP/Contents/Resources/Licenses" "$APP/Contents/Frameworks"
cp "$BIN" "$APP/Contents/MacOS/MeetingCopilotCapture"
sed -e 's/__SHORT_VERSION__/0.1.0/' -e 's/__BUILD_VERSION__/1/' "$CAPTURE/Packaging/MeetingCopilot-Info.plist" > "$APP/Contents/Info.plist"
printf 'APPL????' > "$APP/Contents/PkgInfo"
cp "$CAPTURE/Resources/MeetingCopilot.icns" "$APP/Contents/Resources/"
cp "$CAPTURE/LICENSE" "$APP/Contents/Resources/LICENSE"
cp "$CAPTURE/THIRD-PARTY-NOTICES.md" "$APP/Contents/Resources/"
cp "$DONOR/Contents/Frameworks/liblocalvqe.dylib" "$APP/Contents/Frameworks/"
cp "$DONOR/Contents/Resources/Models/localvqe-v1.4-aec-200K-f32.gguf" "$APP/Contents/Resources/Models/"
cp "$DONOR/Contents/Resources/LocalVQE-verification.json" "$APP/Contents/Resources/"
cp -R "$DONOR/Contents/Resources/Licenses/." "$APP/Contents/Resources/Licenses/"
cp -R "$SPARKLE" "$APP/Contents/Frameworks/"
rm -rf "$APP/Contents/Frameworks/Sparkle.framework/Versions/B/XPCServices"
find "$APP/Contents/Frameworks" -type f -perm +111 -exec codesign --force --sign - --timestamp=none {} \; 2>/dev/null || true
codesign --force --deep --sign - --identifier com.aiagentlbs.meetingcopilot.capture --entitlements "$CAPTURE/Packaging/MeetingCopilot.entitlements" --timestamp=none "$APP"
codesign --verify --strict --verbose=2 "$APP"
echo "$APP"

