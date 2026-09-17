#!/usr/bin/env python3
"""Capture private Zoom frames from the user's GUI session."""

from __future__ import annotations

import signal
import time

from server import FRAME_TRIGGER_FILE, FRAMES_FILE, MeetingFrames, TranscriptState


running = True


def stop(_signal: int, _frame: object) -> None:
    global running
    running = False


def main() -> None:
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    transcript = TranscriptState()
    frames = MeetingFrames(FRAMES_FILE)
    next_capture = 0.0
    trigger_mtime = FRAME_TRIGGER_FILE.stat().st_mtime_ns if FRAME_TRIGGER_FILE.exists() else 0

    # Stay resident between recording files. A manual stop/restart during one
    # real call creates a short marker-free gap; exiting there used to leave
    # the new recording without any screenshots until the launcher was run
    # again.
    while running:
        if MeetingFrames._active_recording_dir() is None:
            next_capture = 0.0
            time.sleep(1)
            continue
        now = time.monotonic()
        current_trigger = FRAME_TRIGGER_FILE.stat().st_mtime_ns if FRAME_TRIGGER_FILE.exists() else 0
        requested = current_trigger > trigger_mtime
        if requested:
            trigger_mtime = current_trigger
        if requested or now >= next_capture:
            transcript.refresh()
            try:
                item = frames.capture(transcript.snapshot())
                speaker = item.get("speaker") or "speaker unknown"
                print(f"frame {item['captured_at']} · {speaker}", flush=True)
            except Exception as exc:
                print(f"frame skipped · {exc}", flush=True)
            next_capture = time.monotonic() + 15
        time.sleep(1)


if __name__ == "__main__":
    main()
