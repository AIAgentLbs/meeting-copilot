#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for tool in say ffmpeg swift xcrun; do
  command -v "$tool" >/dev/null || { echo "Missing local tool: $tool" >&2; exit 1; }
done
fixtures="$(mktemp -d "${TMPDIR:-/tmp}/meeting-language-acceptance.XXXXXX")"
say -v Samantha -r 145 -o "$fixtures/en.aiff" 'Welcome to our project meeting. Today we will review the schedule and discuss the next release. The project is on track. Please confirm the meeting schedule for next week.'
say -v Milena -r 145 -o "$fixtures/ru.aiff" 'Наш проект развивается по плану. Следующая встреча будет во вторник. Давайте обсудим результаты работы и сроки выпуска новой версии.'
say -v 'Mónica' -r 145 -o "$fixtures/es.aiff" 'Nuestro proyecto avanza según lo previsto. La próxima reunión será el martes. Revisemos los resultados del trabajo y el calendario de la nueva versión.'
ffmpeg -v error -i "$fixtures/en.aiff" -i "$fixtures/ru.aiff" \
  -filter_complex '[0:a]aformat=sample_rates=16000:channel_layouts=mono[a];[1:a]aformat=sample_rates=16000:channel_layouts=mono[b];[a][b]concat=n=2:v=0:a=1[out]' \
  -map '[out]' "$fixtures/two.wav"
# Continuous switches also test the model without an artificial reset boundary.
ffmpeg -v error -i "$fixtures/en.aiff" -i "$fixtures/ru.aiff" -i "$fixtures/es.aiff" \
  -filter_complex '[0:a]aformat=sample_rates=16000:channel_layouts=mono[a];[1:a]aformat=sample_rates=16000:channel_layouts=mono[b];[2:a]aformat=sample_rates=16000:channel_layouts=mono[c];[a][b][c]concat=n=3:v=0:a=1[out]' \
  -map '[out]' "$fixtures/three-continuous.wav"
# Natural pauses exercise the same utterance reset as the running capture.
ffmpeg -v error -i "$fixtures/en.aiff" -i "$fixtures/ru.aiff" -i "$fixtures/es.aiff" \
  -filter_complex '[0:a]aformat=sample_rates=16000:channel_layouts=mono,apad=pad_dur=3[a];[1:a]aformat=sample_rates=16000:channel_layouts=mono,apad=pad_dur=3[b];[2:a]aformat=sample_rates=16000:channel_layouts=mono[c];[a][b][c]concat=n=3:v=0:a=1[out]' \
  -map '[out]' "$fixtures/three.wav"
extra=()
developer="$(xcode-select -p)"
if [[ "$developer" == /Library/Developer/CommandLineTools ]]; then
  # CLT 6.3.2 on this Mac does not discover its C++/Testing paths itself.
  sdk="$(xcrun --show-sdk-path)"
  frameworks="$developer/Library/Developer/Frameworks"
  interop="$developer/Library/Developer/usr/lib"
  extra=(-Xcxx -isystem -Xcxx "$sdk/usr/include/c++/v1"
    -Xswiftc -F -Xswiftc "$frameworks" -Xlinker "-F$frameworks"
    -Xlinker -rpath -Xlinker "$frameworks" -Xlinker -rpath -Xlinker "$interop")
fi
cd "$ROOT/capture"
MEETING_COPILOT_ASR_EN_FIXTURE="$fixtures/en.aiff" \
MEETING_COPILOT_ASR_MIXED_FIXTURE="$fixtures/two.wav" \
MEETING_COPILOT_ASR_THREE_FIXTURE="$fixtures/three-continuous.wav" \
MEETING_COPILOT_ASR_THREE_PAUSED_FIXTURE="$fixtures/three.wav" \
  swift test --jobs 2 "${extra[@]}" "$@" --filter LanguageRecognitionIntegrationTests
echo "Synthetic fixtures retained for inspection: $fixtures"
