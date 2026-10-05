#!/usr/bin/env python3
"""Isolated, synthetic HTTP/persistence workload; never use private meeting data.

macOS process-tree RSS/footprint/CPU/disk counters plus logical JSON read volume.
--observe-pid samples a real process tree without starting/stopping it.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request


class Usage(ctypes.Structure):
    _fields_ = [("uuid", ctypes.c_byte * 16)] + [(name, ctypes.c_uint64) for name in (
        "user", "system", "idle_wakeups", "interrupt_wakeups", "pageins", "wired",
        "resident", "footprint", "start", "exit", "child_user", "child_system",
        "child_idle", "child_interrupt", "child_pageins", "child_elapsed", "disk_read", "disk_write")]


def tree_usage(root):
    rows = subprocess.check_output(["ps", "-axo", "pid=,ppid=,rss="], text=True)
    processes = [tuple(map(int, row.split())) for row in rows.splitlines() if row.strip()]
    ids = {root}
    while True:
        new = {pid for pid, parent, _ in processes if parent in ids}
        if new <= ids:
            break
        ids |= new
    lib = ctypes.CDLL("/usr/lib/libproc.dylib")
    total = {"rss_mib": sum(rss for pid, _, rss in processes if pid in ids) / 1024,
             "footprint_mib": 0, "cpu_seconds": 0, "disk_read_bytes": 0, "disk_write_bytes": 0,
             "processes": len(ids)}
    for pid in ids:
        usage = Usage()
        if lib.proc_pid_rusage(pid, 2, ctypes.byref(usage)) == 0:
            total["footprint_mib"] += usage.footprint / 2**20
            # Root's exited children are included; live descendants contribute own CPU.
            total["cpu_seconds"] += (usage.user + usage.system + (usage.child_user + usage.child_system if pid == root else 0)) / 1e9
            total["disk_read_bytes"] += usage.disk_read
            total["disk_write_bytes"] += usage.disk_write
    return total


def worker(args):
    import gc
    import tracemalloc
    sys.path.insert(0, str(Path(args.source) / "copilot/web"))
    import server
    from http.server import ThreadingHTTPServer
    home = Path.home()
    config = home / ".config/meeting-copilot"
    config.mkdir(parents=True, exist_ok=True)
    for name, data in {"active-repos.json": {"repositories": [], "projects": []}, "repos.json": {"repositories": []}, "delivery.json": {}}.items():
        (config / name).write_text(json.dumps(data))
    # 9 MiB historical OCR index, similar in size to the observed private index.
    frames = [{"id": str(i), "meeting_id": "historical", "visual_text": "Synthetic OCR " * 1400,
               "captured_at": "2026-10-01T10:00:00Z", "urls": [], "chat_messages": []} for i in range(500)]
    (config / "frames.json").write_text(json.dumps({"items": frames}))
    server.FRAMES = server.MeetingFrames(config / "frames.json")
    del frames
    reads = {"calls": 0, "bytes": 0}
    original_read = Path.read_text
    def counted(path, *a, **kw):
        value = original_read(path, *a, **kw)
        if path.suffix == ".json":
            reads["calls"] += 1
            reads["bytes"] += len(value.encode())
        return value
    Path.read_text = counted
    tracemalloc.start(8)
    http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    poller = threading.Thread(target=server.TRANSCRIPT.loop, daemon=True)
    poller.start()
    url = f"http://127.0.0.1:{http.server_port}/api/state"
    counters = []
    live = server.TRANSCRIPT.path
    live.parent.mkdir(parents=True, exist_ok=True)
    def phase(name, seconds, payload):
        # The test owns only its isolated HOME. Atomic replacement mirrors Capture.
        temporary = live.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload))
        temporary.replace(live)
        server.TRANSCRIPT.refresh()
        marker = server.ARCHIVE.recordings_root / "synthetic-active" / ".recording.json"
        if args.archive_checks:
            marker.parent.mkdir(parents=True, exist_ok=True)
            if payload.get("status") == "recording":
                marker.write_text("{}")
            else:
                marker.unlink(missing_ok=True)
        start = time.monotonic()
        before, read_before = tree_usage(os.getpid()), dict(reads)
        next_poll = start
        next_archive = start
        peak = before["footprint_mib"]
        while time.monotonic() - start < seconds:
            if time.monotonic() >= next_poll:
                snapshot = json.load(urllib.request.urlopen(url, timeout=30))["transcript"]
                server.ARCHIVE.sync_transcript(snapshot)
                # No cloud report generation/delivery/native ASR is invoked by this fixture.
                next_poll += 2.5
            if args.archive_checks and time.monotonic() >= next_archive:
                # Exercise actual eligibility/history scans, never deliver a report.
                if payload.get("meeting_id"):
                    server.ARCHIVE.needs_report(payload["meeting_id"])
                next_archive += 10
            peak = max(peak, tree_usage(os.getpid())["footprint_mib"])
            time.sleep(.2)
        gc.collect()
        after = tree_usage(os.getpid())
        current, traced_peak = tracemalloc.get_traced_memory()
        counters.append({"phase": name, "seconds": time.monotonic() - start,
            "rss_mib": after["rss_mib"], "footprint_mib": after["footprint_mib"], "peak_footprint_mib": peak,
            "cpu_percent": 100 * (after["cpu_seconds"] - before["cpu_seconds"]) / (time.monotonic() - start),
            "disk_read_bytes": after["disk_read_bytes"] - before["disk_read_bytes"],
            "disk_write_bytes": after["disk_write_bytes"] - before["disk_write_bytes"],
            "json_reads": reads["calls"] - read_before["calls"], "json_read_bytes": reads["bytes"] - read_before["bytes"],
            "python_retained_mib": current / 2**20, "python_peak_mib": traced_peak / 2**20,
            "processes": after["processes"], "threads": threading.active_count(),
            "translations": len(server.TRANSLATIONS.results), "translation_pending": len(server.TRANSLATIONS.pending)})
        print(json.dumps(counters[-1]), flush=True)
    payload = {"version": 1, "source": "meeting-copilot", "meeting_id": "", "title": "Synthetic", "status": "idle", "segments": []}
    phase("idle", args.phase_seconds, payload)
    for number in range(args.meetings):
        segments = [{"source": "microphone" if i % 2 else "system", "timestamp": f"2026-10-05T10:{i//60:02d}:{i%60:02d}Z", "text": "Synthetic meeting speech for bounded processing " * 5} for i in range(args.segments)]
        payload.update(meeting_id=f"synthetic-{number}", status="recording", segments=segments, started_at="2026-10-05T10:00:00Z", updated_at="2026-10-05T10:30:00Z")
        phase(f"recording-{number}", args.phase_seconds, payload)
        payload["status"] = "finished"
        phase(f"finished-{number}", args.phase_seconds, payload)
    phase("long-idle", args.idle_seconds, payload)
    saved = home / ".local/share/meeting-copilot/archive" / payload["meeting_id"] / "meeting.json"
    digest = hashlib.sha256(saved.read_bytes()).hexdigest()
    fresh = server.TranscriptState(live)
    fresh.refresh()
    assert len(fresh.snapshot()["segments"]) == args.segments
    assert hashlib.sha256(saved.read_bytes()).hexdigest() == digest
    hot = tracemalloc.take_snapshot().statistics("lineno")[:10]
    result = {"samples": counters, "retained_allocations": [str(item) for item in hot],
              "archive_sessions": len(list(saved.parent.parent.glob("*/meeting.json"))),
              "restart_transcript_segments": len(fresh.snapshot()["segments"]),
              "method": "synthetic isolated web HTTP + transcript polling + archive persistence; not native audio/ASR or cloud delivery; tracemalloc enabled in both runs",
              "archive_eligibility_checks": args.archive_checks}
    Path(args.output).write_text(json.dumps(result, indent=2))
    if args.assert_stable:
        finished = [item for item in counters if item["phase"].startswith("finished-")]
        assert finished[-1]["python_retained_mib"] - finished[0]["python_retained_mib"] < .25, "retained Python heap grows between meetings"
        assert counters[-1]["python_retained_mib"] - finished[-1]["python_retained_mib"] < .25, "retained heap grows during idle"
        assert len(server.TRANSLATIONS.results) <= args.segments, "translations retain previous meetings"
        assert len(server.TRANSLATIONS.pending) <= 4, "translation work queue is unbounded"
        for number in range(args.meetings):
            canonical = json.loads((saved.parent.parent / f"synthetic-{number}" / "meeting.json").read_text())
            assert len(canonical["segments"]) == args.segments, "archived transcript lost segments"
            assert all(segment["text"] == ("Synthetic meeting speech for bounded processing " * 5).strip() for segment in canonical["segments"]), "archived speech changed"
        print("lifecycle stability and all archived speech checks: ok", flush=True)
    server.TRANSCRIPT.stop.set()
    server.TRANSCRIPT.trigger.set()
    http.shutdown()
    http.server_close()
    server.TRANSLATIONS.pool.shutdown(wait=True, cancel_futures=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output", required=True)
    parser.add_argument("--meetings", type=int, default=8)
    parser.add_argument("--segments", type=int, default=500)
    parser.add_argument("--phase-seconds", type=float, default=3)
    parser.add_argument("--idle-seconds", type=float, default=60)
    parser.add_argument("--observe-pid", type=int)
    parser.add_argument("--archive-checks", action="store_true", help="Include real report eligibility/history scans every 10 seconds")
    parser.add_argument("--assert-stable", action="store_true", help="Fail on retained-heap growth, historical translations or missing speech")
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.observe_pid:
        samples = []
        start = time.monotonic()
        while time.monotonic() - start < args.idle_seconds:
            samples.append({"at": time.monotonic() - start, **tree_usage(args.observe_pid)})
            time.sleep(2)
        Path(args.output).write_text(json.dumps(samples, indent=2))
        print(json.dumps(samples[-1]))
    elif args.worker:
        worker(args)
    else:
        with tempfile.TemporaryDirectory(prefix="copilot-memory-home-") as directory:
            command = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:], "--worker"]
            subprocess.run(command, env={**os.environ, "HOME": directory}, check=True)


if __name__ == "__main__":
    main()
