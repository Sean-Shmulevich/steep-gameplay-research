# Gameplay jobs in the owned engine

Set a scenario's `execution_mode` to `mixed` to run physics, environment,
scoring, animation and camera through `MixedScheduler`. The default is `direct`.
Both modes call the same numerical phase methods in the same order. This is an
integration of the independent engine with the executable scheduler reference.
It does not establish the original game's gameplay job topology or threading.

## Contract

`Engine.step()` and `Engine.advance()` keep their existing interfaces. Every
planned physics substep creates this graph:

```text
physics range ['player']
  -> environment callback
  -> scoring callback
  -> animation callback
  -> camera callback
  -> ready terminal
```

Each callback performs the real phase work. Physics includes contact and
obstacle handling. Scoring consumes its landing diagnostics. Animation consumes
the updated body and controls. Camera consumes the same updated body. Environment
updates its own state; this change does not add a weather-to-grip connection.

The graph is designed here. The request, dependency, reservation and finalization
rules it exercises are documented in
[Mixed scheduler implementation](MIXED_SCHEDULER_IMPLEMENTATION.md), particularly
the executable API and the ordinary, callback and terminal job contracts.
The graph has no conditional branches, credit gates or overlapping frame roots.
Those features remain available in the standalone scheduler reference.

The internal `gameplay_jobs.run(phases, context, trace, **trace_fields)` accepts
all five `phase(context)` callables. It returns an inspectable drained scheduler
snapshot. Physics has one synthetic receiver named `player`; it is not a native
object identifier. Handler version `owned-gameplay-v1` describes this adapter's
bindings. It is not a hash of arbitrary Python code or closure contents.

Time remains explicit. Every phase receives the selected elapsed time. Derivative
time remains recorded in diagnostics as before; this integration does not change
the numerical controllers to consume it. Scheduler frame planning is independent
of this dispatch choice. A frame with no planned substeps creates no job graph.

## Lifetime and transaction boundary

The graph is created and drained for each substep, then discarded. No graph,
dispatch token, callable or scheduler identity enters the numerical state or
checkpoint. This policy deliberately avoids inventing persistent native graph
ownership. The current Engine is used serially; callers needing exclusion use
the existing scheduler controller.

Only the enclosing Engine commits the tick, time, events and `last_good` state.
It validates the body and complete JSON state after all five phases and the
terminal return. A callback exception stops later jobs. The Engine restores the
substep state, records an incident and emits its abort event. `advance()` retains
its wider transaction: a later substep failure restores the entire outer frame,
including earlier substeps' state, events and `last_good`. Trace and incident
records survive to explain the failed attempt. `step()` retains its existing
pause-on-failure behavior; `advance()` restores the pre-frame pause state.

These transactions cover owned simulation state. They cannot undo a caller's
external side effects. This integration exposes no arbitrary phase-mod registry,
native hooks, concurrent executor or mid-dispatch checkpoint restore.

## Inspection and replay

Forwarded trace records have `kind: gameplay_job` and `job_event` containing the
mixed scheduler's event kind. They also carry the current `tick`, substep
`invocation`, `frame_invocation` and `input_generation`. The events surround the
actual physics and animation calls, so reservation, body entry, body return,
terminal begin and committed simulation state can be inspected separately.

The Engine trace bounds retention and reports dropped records. Each transient
graph also keeps a bounded local trace for its returned inspection snapshot.
Overflow does not gate simulation work. Event sequence numbers describe this
serial owned execution; they are not native thread timestamps.

Direct and mixed modes produce identical full state hashes for identical initial
conditions and commands. Their scenario hashes differ because the execution mode
is explicit. Checkpoints retain the mode and trace, while replay reconstructs
fresh graphs from the recorded commands. Trace invocation numbers can differ
between modes because mixed execution emits more events; these numbers never
enter physical state.

## Validation

`tests/test_engine_gameplay_jobs.py` checks separate callback execution, drained
terminal accounting, interleaved phase traces, early failure blocking successors,
invalid configuration rejection, and rigid contact plus graph-animation parity.
`tests/test_engine_gameplay_integration.py` independently checks all five sports,
JSON checkpoint continuation, replay, controller restoration, trace overflow and
whole-frame rollback after camera writes on a later substep.

The runnable example is `python3 -m engine.examples.gameplay_scheduler_probe`.
Its direct-versus-mixed comparisons test the independent engine's consistency.
They do not validate the original game's numerical behavior.
