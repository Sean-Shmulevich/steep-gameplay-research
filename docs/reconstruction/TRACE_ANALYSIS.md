# Reading owned-engine trace outcomes

`engine.trace_analysis.analyze(trace_snapshot)` returns a JSON report without
changing the trace or advancing simulation. It validates the envelope with
`Trace.restore`. Invalid sequence accounting, malformed identifiers and malformed
frame plans raise `ValueError`. Contradictory event order is retained in the
report's `anomalies` rather than discarded.

This analyzes the events described in [Gameplay job integration](GAMEPLAY_JOB_INTEGRATION.md).
The five-phase order is the owned engine's designed graph. It is not a discovery
of the original game's topology. Sequence numbers establish serial event order,
not wall-clock durations, native timing or concurrent happens-before relations.

## Report fields

- `complete` means all emitted records were retained. It does not mean a run
  succeeded or all active attempts ended.
- `status` is `incomplete` when records were dropped or attempts remain unresolved,
  `anomalous` for complete, resolved but contradictory evidence, and `complete`
  otherwise. A fully recorded failed run can have status `complete`.
- `counts` reports retained and attempted records, drops, frames and substeps.
- `frames` identifies each outer attempt by `frame_invocation`, its entry and plan
  sequences, planned substep count, associated substeps and committed, aborted or
  unresolved outcome. `verified` is conservative: it is false when any anomaly
  exists in the report or the trace dropped records.
- `substeps` identifies attempts by `invocation`, never by tick alone. Retrying a
  rolled-back tick creates a separate attempt. Entry fields retain tick, elapsed
  and derivative time and input generation. Ending fields retain available tick,
  error type and committed state hash.
- `phases` distinguishes callback entry, callback return, returned worker dispatch
  accounting and numerical observations. `terminal_begins` is separate. A ready
  terminal can begin before camera dispatch accounting returns, so it is not
  counted as worker completion.
- `failures` preserves observed handler failure details. Global and per-substep
  anomalies record ordering or missing-evidence contradictions.

A substep's `local_outcome` records its own commit, abort or unresolved state.
Its `effective_outcome` also considers the outer transaction. An outer abort
marks all its entered substeps `rolled_back`, including earlier local commits.
A local commit in an unfinished outer frame is `pending_frame`. Dropped records
prevent unqualified success; retained commits become
`unverified_incomplete_trace` unless an observed outer abort already establishes
rollback. Always check report completeness as well as individual outcomes.

Direct execution has physics and animation observations but no job callback
records. Their absence is valid. Until both numerical observations establish
that path, mode remains `direct_or_unobserved`; an early truncated mixed attempt
is therefore not mislabeled direct. Observed job events establish `mixed` mode.

## Use

```python
from engine.trace_analysis import analyze
report = analyze(engine.trace.snapshot())
for attempt in report['substeps']:
    print(attempt['invocation'], attempt['local_outcome'],
          attempt['effective_outcome'])
```

The inspector also exposes a read-only `GET /trace/analysis` endpoint. Save the
original trace alongside any report when investigating a failure. The report is
a correlation summary, not a replacement for the underlying records.

## Validation and limits

`tests/test_engine_trace_analysis.py` covers actual direct and mixed execution,
an exception on a later substep followed by retry, overflow, a pending frame,
zero-substep frames, invalid envelopes and IDs, malformed ordering, and terminal
begin without worker completion. Analysis does not inspect gameplay correctness,
recompute state hashes, validate native job identity, or infer absent callbacks.
Unknown event kinds are left outside this narrow correlation model.


## Optional phase-state capture

Set scenario `trace.capture_phase_state` to true to retain entry and normal-return
observations for each owned gameplay phase. The option is false by default and
requires a JSON boolean. It applies equally to direct and mixed dispatch.

Each `phase_state` row carries phase, boundary, tick, substep invocation, outer
frame invocation and input generation. State is copied when emitted. Physics
captures body and controls; environment captures its state; scoring captures body
and scoring; animation captures body, controls, animation clocks/state and the
full evaluated pose; camera captures body and camera state. This makes the
physics-to-animation input relationship inspectable without using wall timers.

These records describe observations inside an attempted substep. A phase return
does not imply the outer frame committed. Use the analyzer's invocation/frame
outcomes before treating an observation as retained simulation history. Failure
before a normal return emits no return observation for that phase. A later abort
can invalidate earlier phase observations while retaining them as Engine-level
diagnostics. SchedulerController's wider rollback restores its prior trace on
execution failure; its incident record now retains a separate bounded failure
excerpt rather than merging the failed attempt into the restored trace.
The analyzer treats these as supplementary observations; it does not yet audit
phase-state schema or compare their payloads.

Capture does not affect numerical state or replay hashes in tested direct/mixed
paths. It adds ten records per successful five-phase substep, with potentially
large pose payloads. The existing record capacity and explicit drop accounting
still apply; capacity bounds record count, not payload bytes. Read captures through
the controller's `/trace` endpoint. No original-game animation or native thread
causality is inferred from these owned execution records.


## Controller failure excerpts

Execution failures now preserve `failure_trace` inside the controller incident
before restoring the engine. The main trace, numerical state and command history
still roll back. The incident identifies `generation_before_failure`, since trace
sequence numbers can be reused after rollback. Its error names the failed operation.

An excerpt retains at most the last 64 captured records from that attempted
operation, including optional phase-state observations. `first_sequence` and
`next_sequence` describe the attempted interval. `dropped_at_capture` counts events
never retained by the original trace capacity; `omitted_by_excerpt` counts retained
records excluded by the 64-record limit. `complete` means neither loss occurred.
It does not mean the operation succeeded or all relevant internal behavior was
instrumented. An operation rejected before any trace event may have a complete,
empty excerpt.

These excerpts retain original sequence values and are not standalone restorable
Trace envelopes. Do not pass them directly to the ordinary trace analyzer or merge
them with a later successful retry. The incident list and excerpts survive owned
controller checkpoints and are returned through the controller HTTP snapshots.
The existing 100-incident limit remains. Both limits bound record counts, not the
byte size of optional pose payloads.

If collecting an excerpt raises an exception, the incident instead contains
`complete: false` and `capture_error`. Rollback and the original execution exception
remain authoritative. No native game crash dump or payload is collected.
