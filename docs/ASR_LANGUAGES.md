# Automatic meeting-language recognition

Speech recognition is independent of interface and summary language. The legacy
`transcription.language` preference must not become a decoder prompt, a script
filter or a two-language whitelist. Live recognition uses the full multilingual
Nemotron model and its native `auto` prompt on independent microphone/system
streams. Each meeting starts new decoder state.

Ending an utterance flushes its final words, then resets neural/language state
without unloading the model. `finish()` alone clears tokens but retains that
state. Callback generations reject late results from a closed utterance;
per-channel partial state is cleared so a repeated phrase is not lost.

After a meeting, the web bridge adopts the recorder's complete final transcript
when it appears, even if the live JSON has not changed. It validates the physical
recording start time and preserves audio and live evidence on disk. Missing,
malformed, empty or mismatched final files leave the live version intact.
Live speaker evidence now carries the first and last actual decoded observation.
Final text inherits a live voice only with unambiguous overlapping evidence;
legacy blocks without an observed end remain unassigned, never extrapolated
across a disabled/stalled recognizer. Original live files are preserved.

## Reproduce locally

Run `bash scripts/check-language-switching.sh` on macOS with the multilingual
live model already installed. It synthesizes public example speech locally and
runs actual CoreML recognition: English with a legacy Russian preference,
English/Russian switching, and English/Russian/Spanish with and without added
utterance pauses. Use the exact installed Spanish voice name `Mónica`;
`Monica` without the accent produces a different, unsuitable speech fixture on
this Mac. Models are not downloaded by these tests; no real meeting
audio or transcript is added to Git. Fixtures stay in a temporary directory.

These checks are not a guarantee of perfect recognition of arbitrary speech,
noise, accents, overlap or every code-switch. Synthetic speech acceptance is
not a substitute for a consented multilingual real-call acceptance recording.
Provider-specific multilingual cloud behavior has not been certified by local
CoreML tests. Parakeet v2 is English-only; multilingual use requires v3.

Web regression: `python3 -m unittest discover -s copilot/web -p 'test_*.py' -q`.
Swift policy/setup regressions and the complete suite run with `swift test`;
the acceptance script includes the explicit framework/C++ paths required by
this Mac's CLT 6.3.2 installation.
