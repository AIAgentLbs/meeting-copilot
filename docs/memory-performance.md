# Memory and background-work audit — 2026-10-05

## Scope and installed state

Changes are in the source repository, not just the installed web copy:
`copilot/web/server.py`, `archive.py`, `live_translation.py`.
The matching three files are installed in `~/.local/share/meeting-copilot/web`.
The existing LaunchAgent is restored, running with `RunAtLoad=true` and
`KeepAlive=true`; one listener serves `127.0.0.1:43121`.
Native Capture, recognition models, recording settings, recovery, delivery
and automatic start/stop rules were not disabled or replaced. Capture was
not restarted while recording. No public release or repository commit was made.

## Evidence and minimal fixes

- Unchanged live JSON was reparsed each second. Refresh now compares file
  identity, size and nanosecond mtime. Recovery-tail changes invalidate the
  snapshot independently; unsuccessful reads are not cached.
- State polling repeatedly rebuilt annotations and parsed the large historical
  frame index just to display a title. A single derived snapshot is reused;
  transcript, canonical speaker edits, recovery, frames and translation
  revisions invalidate it. Live health timestamps remain fresh.
- Repository counts now retain only two scalar count entries keyed by file
  stat, not complete repository manifests.
- Translation results/retry state retained older meetings. Switching meetings
  releases old results and cancels queued old work; in-flight old results are
  discarded. There are still two workers, but at most four pending tasks rather
  than forty. Current-meeting translations and original speech remain available.
- Copilot replies grew without a RAM limit even though persistence/restart
  already retained only 100 messages. RAM now matches that existing limit;
  archive, journal, transcripts and the on-disk retention policy are unchanged.
- Report eligibility scanned the full archive before checking active capture.
  It now checks the existing recording markers first. This changes no delivery
  policy: an active recording already prevented report finalization. Transcript
  persistence still runs every ten seconds.
- Chain/history operations repeatedly parsed the same journal/chat/frame
  indexes for each meeting. Journal/chat reuse is operation-scoped and
  thread-local, with unconditional cleanup, not an accumulating history cache.
  The web archive shares the already loaded frame index; standalone archive
  consumers parse it once per operation. New operations see updated files.

No evidence was found here proving a long-lived leak responsible for the
previously observed 416–856 MB footprint. Retained translation history and
repeat allocation/read paths are demonstrated separately. Short samples do
not establish persistently high CPU. Capture/model memory and temporary
Codex/image-analysis subprocesses are not Python heap leaks.

## Reproduce safely

The harness starts a separate Python process with an isolated temporary HOME,
eight synthetic meetings of 500 turns and a historical OCR index of about
9 MiB. It exercises HTTP state polling, live-file refresh, archive persistence
and real report-eligibility/history scans, including active-capture markers.
It does not start native capture/ASR, screenshot analysis, report delivery or
Google operations. It does not read private meeting content.

```sh
cd /Users/m/code/aiagentlbs/meeting-copilot
python3 scripts/profile-copilot-memory.py \
  --archive-checks --assert-stable --meetings 8 --segments 500 \
  --idle-seconds 3600 --output /tmp/copilot-memory-after.json
python3 -m unittest discover -s copilot/web -p 'test_*.py'
python3 copilot/web/server.py --self-test
```

For a baseline, pass `--source` pointing to a preserved pre-change repository
snapshot and omit `--assert-stable`. To sample a running process and all its
descendants without restarting anything:

```sh
python3 scripts/profile-copilot-memory.py --observe-pid PID \
  --idle-seconds 60 --output /tmp/copilot-process-tree.json
```

Measurements include RSS, physical footprint, CPU time, physical disk counters,
logical JSON read bytes, thread counts, translation state and retained Python
allocations. RSS and footprint are different metrics. CPU percent is relative
to one core, not the whole multi-core Mac. Physical disk counters are affected
by page-ins, filesystem cache and system swap pressure; logical JSON bytes
must not be described as physical disk traffic. Polling the process tree itself
adds overhead; when sampling itself, the synthetic worker briefly includes its
`ps` child. Baseline and after runs use the same instrumentation.

## Verification and limits

- 130 web tests and the server self-test pass. New regressions cover unchanged
  JSON identity, recovered-tail invalidation, annotation reuse, translation
  lifecycle/queue bounds, active-marker report gating, shared-index reuse and
  refresh between operations and the existing 100-message retention contract.
  Existing archive, delivery, recovery and manual
  speaker-edit tests still pass.
- Eight sequential synthetic archives retain all 500 speech turns each.
  The stability assertion rejects more than 0.25 MiB retained Python heap
  growth between the first/last finished meeting or over the idle phase, old
  meeting translation retention and oversized translation queues. This allows
  small instrumentation/cache warm-up allocations; it is not a zero-growth claim.
- Live web restart restored the same real meeting and all 165 established
  turns. The latest provisional turn of each channel is excluded from the
  equality comparison because Capture updates its text while speech continues.
  Native Capture PID was unchanged and both CAF tracks grew afterward.
- Hash/readback audit of 201 existing files: no missing files; the original
  text of 65 archived meetings was unchanged. The only changed original files
  were the two CAF tracks of the ongoing recording, which were growing.
- Actual native idle and recording trees were sampled separately. The real
  call stayed active during final validation; a controlled actual finished/idle
  comparison was not forced by stopping it. Those phases are covered by the
  isolated workload, not by a claimed real-call before/after experiment.
- The completed idle soak is three minutes, not forty hours. A longer run is
  reproducible with the command above and remains a release gate. The fixture
  uses a fixed historical frame index, so it does not prove constant RAM for
  indefinitely growing screenshot/chat history. Persistent meeting data is
  preserved, not truncated to make the memory graph look flat.
- Temporary analysis helpers can still dominate the real process tree. Their
  demand varies with call content; two short real samples are not a controlled
  causal before/after performance comparison. Do not market the fixture's
  footprint as the complete live system's memory budget.

Detailed private evidence and the pre-change source snapshot are retained in
`~/.local/share/meeting-copilot/memory-audit-I4Hvwj/`; no meeting data was copied
into the repository. See the measurement summary below.

## Measurement summary

Matched isolated workload, eight meetings, 500 turns each, fixed historical
OCR index. Values below are MiB; CPU includes measurement overhead. Recording
and finished values are means of eight phase-end samples, not a measured
native/ASR meeting. The pre-change snapshot contains this checkout's previous
local work, not merely a clean Git HEAD.

- Initial idle: footprint **65.5 → 35.8**, RSS **69.9 → 37.0**, CPU
  **0.51% → 0.27%**. These are short warm-up phases, not a long-idle average.
- Recording: footprint **80.8 → 43.0**, RSS **64.2 → 38.9**, CPU
  **1.17% → 0.60%**. Logical JSON bytes per phase **97.6 MB → 0.73 MB**;
  the wall times differed (~3.4/~3.9 seconds), so these are not I/O rates.
- Finished: footprint **78.9 → 43.4**, RSS **66.7 → 39.0**, CPU
  **1.43% → 0.86%**. Logical JSON per phase **159.4 MB → 5.86 MB**;
  wall times ~3.6/~5.4 seconds under changing machine pressure.
- Post-meeting idle: pre-change 60 seconds, final 181 seconds. Footprint at end
  **53.2 → 44.0**; sampled peak **85.8 → 44.0**; RSS **40.6 → 37.5**;
  CPU **1.04% → 0.84%**. Normalized logical JSON reads **1,548 → 66.7 MB/min**.
  Physical reads **51.8 → 24.2 MB/min**; physical writes zero in both idle
  phases. Disk-read improvement is less portable than logical-read reduction
  because it depends on cache/page-in pressure. There is no demonstrated
  constant high-CPU problem in these samples.
- Retained Python heap after the first/eighth finished meeting in the final
  workload: **1.209 → 1.243 MiB**, then **1.362 MiB** after the three-minute
  idle phase. Translation entries belong only to the current meeting (300 at
  the last sample), versus 1,500 across meetings in the baseline. No queued
  work remained at the sampled ends. Five Python threads after worker startup
  stayed five across all eight meetings; no per-meeting thread accumulation.
- Physical reads/writes during the short recording and finished fixture phases
  are in the raw JSON, separately from logical reads. Per-phase recording
  reads averaged 1.74/3.91 MB and writes 0.249/0.249 MB (before/after);
  finished reads 2.21/5.19 MB and writes 0.246/0.246 MB. These noisy physical
  phase samples did not all improve; this is not concealed as zero I/O.

Actual Mac process trees, separate 30-second read-only samples during the call:

- Native idle before the call: footprint **48.7 MiB**, CPU **0.01%**,
  reads **0.39 MB**, writes zero.
- Native recording: footprint **125–132 MiB**, CPU **1.01%**, reads
  **8.40 MB**, writes **0.79 MB**. A later sample: **123–132 MiB**, **1.05%**,
  reads **11.70 MB**, writes **1.79 MB**. Native was unchanged.
- Web tree before the final archive optimization: footprint **241–1,218 MiB**,
  up to ten processes, CPU **1.20%**, reads **78.32 MB**, writes **9.46 MB**.
  The large transient includes analysis helpers, not just the Python parent.
- A final installed recording sample with no active helper subprocess:
  footprint **60.8–62.7 MiB**, RSS **5.8–15.8 MiB**, one process,
  CPU **0.079%**, reads **6.57 MB**, writes **0.27 MB**. Low RSS under this
  Mac's memory pressure does not mean the footprint is zero. This is a quiet
  recording interval, not evidence that future image/LLM jobs cannot peak higher.

The numerical benchmark was taken after all hot-path changes and before the
100-message RAM cap; its fixture does not generate Copilot chat replies, so
the cap does not affect those numbers. That additional fix is unit-tested.
