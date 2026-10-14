# Independent engine implementation

This is a runnable Python research engine assembled from recovered local kernels and explicitly designed policies. It is not original engine source, a complete game port or a claim of full behavioral equivalence. No original assets are required or bundled. Python 3.10+ and its standard library are sufficient.

## Run

From the repository root:

```sh
python3 -m engine.cli --ticks 1200 --sport snowboard
python3 -m engine.cli --sport paraglider --ticks 1200 --output /tmp/flight.json
python3 -m engine.cli --replay /tmp/flight.json
python3 -m engine.cli --serve --port 8770
python3 -m unittest discover -s tests -v
```

Open http://127.0.0.1:8770 for the diagnostic terrain/skeleton view. The server binds loopback only. All clients share one engine. Run/pause, individual steps, checkpoints, sport selection and replay export are available. A/D steer, W tucks or walks forward, S brakes, Space charges then releases a jump, Q/E control flips. Click outside the sport selector to return keyboard control. This is an inspector; visual fidelity is intentionally limited.

## Python API

```python
from engine.runtime import Engine
from engine.replay import record, replay

engine = Engine({'sport': 'snowboard'})
engine.set_input({'jump': True})
engine.step(90)
checkpoint = engine.checkpoint()
engine.set_input({'steer': .3, 'flip': .4})
engine.step(240)
assert replay(record(engine)).state_hash() == engine.state_hash()
engine.restore(checkpoint)
```

`step(n)` advances n fixed development ticks, default 1/120 second. `advance(frame_dt)` uses the configured scheduler, either fixed accumulation or the recovered subdivision policy with optional smoothing. They are distinct APIs; step does not simulate an outer-frame scheduler invocation. Both are recorded for replay. The subdivision derivative interval is recorded separately; the point controller currently consumes elapsed time only.

`snapshot()` returns a detached published-state copy. Checkpoints include body/controller histories, input state, scheduler, scoring, environment, animation, camera and scenario identity. Restoring a checkpoint starts a new replay base. Runtime failures roll back the tick and log a bounded incident record; `recover()` resumes the last good state after the caller repairs the fault. Frame advance is transactional across its selected substeps. This is a designed fault-containment policy, not recovered original crash recovery.

## Modules and evidence

| Module | Working scope | Important limitation |
| --- | --- | --- |
| runtime/replay | Stepping, checkpoints, journals, hashes, recovery | Same-runtime determinism only; not original-game replay |
| scheduler | Fixed mode; recovered subdivision, smoothing ring and frequency table; per-frame plans | Native execution ownership and submission exclusion remain unresolved |
| input | Validated per-command input snapshots | Generations are our design; original writer freshness open |
| world | Analytic slope/bumps, material patches, swept cylindrical obstacles | Synthetic collision world |
| physics | Snow/ski point contact, steering, brake, jump, independent air rotation, walking | Designed integration/controller; not the original full hull/constraint solver |
| rigid | Optional six-cell hull, pressure/contact impulses, rotating inertia and world angular momentum | Synthetic hull, volume-based weights, controls and substrate; not full original constraints |
| contact | Clipped tetrahedron, pressure/contact impulses, point impulse application | Standalone probe, also used by optional rigid_cells mode |
| domains | Wingsuit/paraglider local response laws, environment clock/weather overlays | Synthetic presets and selectors; unknown zones/track evaluator |
| animation | Rig/clip validation, crossfade/additive, hierarchy, palette; optional recovered 60 Hz sampling and inclusive wrap | Default sampling/selection designed; active addon merge unresolved |
| graph | Serializable clip/blend/axial/additive/mask/select graph; separate readiness kernel | Graph wiring and clock policy are caller designs, not the recovered active rider graph |
| procedural | Recovered limb target, weighted orientation and landing alignment | Explicit caller mapping/order; not full-body IK |
| camera | Recovered spring math with an explicit follow policy | Default distances/FOV and arbitration are designed |
| scoring | Recovered local quantization/commit with flight detector | Detector and event ownership are designed |
| inspection | Rig bindings, sign-invariant pose comparison, aligned trace differences | Inputs must share frames/units and compatible joints |
| assets/archive/asset_adapter | Evidence labels, read-only v27 index and compression framing, typed local pose adapter | Supported observed layouts only; no repacker, automatic rig merge or root-motion extraction |
| server/view | HTTP operations and diagnostic canvas | Local research interface, not production renderer |

The reference modules retain provenance in REFERENCE_MANIFEST.json. Default rigs, clips, geometry and tuning are synthetic. Studio-authored and video-estimated resources have distinct categories and must never silently become recovered evidence.

## Scenarios and mods

A scenario is a schema-version-1 JSON object with sport, world, body, physics_mode and optional physics, rigid, air, environment, scheduler, scoring, camera and resources configuration. Unknown top-level fields fail. See [the shared contract](CONTRACT.md) and module docstrings for exact field schemas. Configurations are immutable by convention during a run; use a new scenario or a checkpoint-aware API rather than editing live dictionaries behind the journal.

A resource bundle has `category`, `rig` and `clips`; their schema is documented in animation.py. Supply original resources only locally with appropriate access. Missing clip channels remain visible in diagnostics. No heuristic base/addon rig merge is disguised as recovered behavior.

The JSON API accepts POST /api with op: input, step, advance, run, pause, reset, checkpoint, restore, recover, resources, tune, inspect, cell or limb. `run` includes actions and count; `cell` supplies vertices, surface, dt and settings; `limb` supplies a request matching procedural.limb_target. GET /state, /resources, /trace, /trace/analysis and /replay return JSON. Invalid operations return a structured error. Standalone probes do not mutate the engine.

## Validation and next passes

See [implementation progress](PROGRESS.md). Tests cover formulas, meaningful boundaries, phase/state transitions, mutation isolation, all sport runtimes, replay after restoration, failed-tick rollback, stable slope contact and HTTP controls. Passing tests establishes these contracts, not recovered coverage of the full game.

For the optional hull mode, use `Engine({"physics_mode":"rigid_cells"})`. It is supported for snowboard and ski, with dt at most 1/60 second. The default point controller remains available for comparison. `python3 -m engine.scenarios --ticks 3600` runs all five sports through scripted controls and verifies exact replay hashes.

## Animation graphs and local assets

Set `scenario.animation.graph` to a version-1 graph with `root` and a `nodes` map. Nodes support clip playback, ordered weighted blending, axial interpolation, additive deltas, per-bone byte masks and explicit selectors. Scalar parameters accept constants or `{"input":"speed"}` references. Inputs include controls, speed, grounded and air. See [graph tests](../tests/test_engine_pose_graph.py) for executable examples. All node clocks are checkpointed; shared nodes evaluate once per invocation and inactive clocks retain their time. Those scheduling policies are independent implementation choices.

Compatibility playback uses an integer 60 Hz query to select a key interval, then continuous time to interpolate within that interval. It does not quantize the entire pose to 60 Hz. Translation and rotation streams can have different key times. Unbound tracks and unsupported auxiliary channels are reported.

`Engine.replace_resources(bundle)` validates and replaces visual resources without moving the body. `Engine.tune(changes)` accepts physics, air, rigid, camera, environment and scoring sections. Both create a new replay base so later replay includes the new configuration. Invalid replacements leave the current state intact. HTTP operations use `{"op":"resources","bundle":...}` and `{"op":"tune","changes":...}`.

The optional local importer accepts the existing decoded pose-assembly JSON schema:

```sh
python3 -m engine.importer /private/path/decoded.json --rig male --clip CLIP_NAME --unit-scale 1 --loop --output /tmp/private-scene.json
python3 -m engine.cli --scenario /tmp/private-scene.json --serve --port 8771
```

The scale and loop policy are explicit caller choices. The importer rejects output inside this public source repository. It does not infer active gameplay bindings, merge addon rigs, or extract root motion. The inspector displays the supplied resource category.

`engine.archive.Archive` reads the observed version-27 archive index. `decode_blocks` validates observed compression framing, Adler checksums and output bounds; `NativeCodecs` optionally calls locally installed Zstandard/LZO libraries. Explicit library paths may be needed when system discovery fails. The simulation itself has no native codec dependency. These APIs read local files without modifying archives. See [validation scope](VALIDATION.md) before extending format support.

## Scheduler experiments and phase traces

[The scheduler roadmap](SCHEDULER_ROADMAP.md) is the current primary work plan. Run the supplied headless experiment with:

```sh
python3 -m engine.experiments engine/examples/scheduler_probe.json --output /tmp/scheduler-report.json
```

Commands commit input, advance explicit outer-frame intervals, step development ticks, checkpoint/restore, pause, or assert a state value. Reports include exact replay comparison, scheduler decisions, incidents and bounded phase traces. `advance` is also available over HTTP with `dt` in seconds. `step` intentionally bypasses frame planning.

Set `scheduler.mode` to `subdivision` and `smoothing_enabled` to true to use the recovered ring/table arithmetic. Both elapsed and derivative intervals remain exposed. `scheduler.last_plan` records planned work; committed execution is identified separately in the trace. `trace.capacity` controls a nonwrapping buffer, and overflow sets `complete=false` with an explicit drop count. Read operations do not advance the simulation. These are owned-runtime guarantees.

## Additional animation building blocks

The following standalone modules are available for explicit callers. Their policies do not automatically become the default rider graph:

- `rig_assembly.assemble`: base/addon index maps, collision diagnostics and caller-selected duplicate/attachment policies.
- `root_motion.extract_motion`: explicit channel trajectory and conditional model-space removal. Loop accumulation is designed; physics coupling is absent.
- `pose_pipeline.apply`: ordered named-bone orientation, landing alignment and intermediate limb targets. It does not claim a full-body IK solve.
- `motion_state.update`: checkpointed observation of takeoff, flight, landing and crash phases. Selection and recovery durations are configurable substitutes.
- `providers.initialize` and `resolve`: recovered local key/backing and lookup behavior, including output writes on an unavailable match. Original provider lifetime and authored UID conversion remain open.

Tests use synthetic clips and rigs. No new original asset payloads are distributed.

## Owned dependency executor

`engine.jobs.JobExecutor` provides an experimental serial job API. Jobs declare dependencies and versioned handlers. Claiming retains a callback without executing it; only completed prerequisites release dependents. Handler replacement, removal and reset require no claimed/running callbacks. Failure blocks dependents and preserves an inspectable error.

```python
from engine.jobs import JobExecutor

handlers = {
    'advance': {'version': 'demo-1', 'callback': lambda engine: engine.advance(1/60)['tick']},
    'snapshot': {'version': 'demo-1', 'callback': lambda engine: engine.snapshot()},
}
jobs = JobExecutor([
    {'id': 'frame', 'handler': 'advance'},
    {'id': 'inspect', 'handler': 'snapshot', 'depends_on': ['frame']},
], handlers)
results = jobs.run_ready(engine)
```

This executor is standalone; the gameplay runtime has not been refactored into its jobs. It is a testable boundary for future mods, not a native scheduler hook. Quiescent snapshots can be restored with matching handler version tokens. Python callables, closure state and callback side effects require caller ownership; version tokens alone cannot prove code identity, and side effects are not rolled back. This API is not a sandbox for untrusted mods.

## Exclusive owned-runtime stepping

`SchedulerController` owns one Engine and serializes every submission. Pause waits for the current operation and returns a generation-qualified token. A paused token permits one developer tick or one planned outer frame; both return to the paused state before releasing the lock. Resume/reset/restore invalidate stale tokens. This implements an explicit submission gate in our runtime, not an original-process pause mechanism.

```python
from engine.control import SchedulerController

controller = SchedulerController({'scheduler': {
    'mode': 'subdivision', 'smoothing_enabled': True}})
token = controller.pause()
result = controller.step_frame_once(token, 1/60, {'steer': .3})
assert result['control']['paused']
checkpoint = controller.checkpoint()
controller.step_once(token)  # One configured fixed developer tick.
token = controller.restore(checkpoint)
controller.resume(token)
controller.submit_frame(1/60)
```

Use `snapshot()` for copied state and trace, and `export_replay()` for an owned replay record. Neither advances time. Frame failure rolls back owned input/state/replay changes, invalidates the old token, and leaves submissions excluded. Call `pause()` to obtain the new token. Native callbacks and external side effects are outside this rollback. An Engine handed to a controller must not be called directly elsewhere. The existing browser server still uses the basic Engine API; this controller is currently a Python API.

`membership.copy_registered_receivers(source, destination)` preserves the recovered conditional copy rule: a nonempty stable source replaces the destination, while an empty source retains it. The caller owns locking, lifetime and request/reset boundaries. It is a local semantic helper, not proof that a retained receiver belongs to a current native request.

`action_sample.combine_directions` and `publish_vector` implement the recovered two-axis action's local arithmetic with explicit query outcomes and processed-vector inputs. The default reciprocal-square-root seed is a labeled scalar substitute; callers may supply a native estimate for the recovered refinement. The kernel preserves processed magnitude and does not replace the sampled vector with its normalized direction. It is not automatically mapped to player controls.

`membership.claim_range` computes the recovered ordinary tail-claim proposal. `configured_chunk` exposes the ordinary chunk setter. Both leave native compare/exchange, receiver lifetime and request ownership to the caller. No remaining entries means no new claims, not completed callbacks.

`action_sample.evaluate_two_axis` composes direction queries, an explicit processor policy and publication. Choose `default` for the recovered pass-through processor, `bypass` for a bypassed callback, or `supplied` with an already processed vector. Missing configured behavior is rejected instead of silently using fallback. The default processor retains its first-use marker across calls but does not alter diagonal magnitude. This pipeline remains a local action-type API, not a claim that the active rider selects it.

## Mixed scheduler probe

Run `python3 -m engine.examples.mixed_scheduler_probe` to print a synthetic three-cycle report from the recovered scheduler rules. It executes motion receivers, bypasses them for one cycle, then executes them again. The EndFrame-like callback submits the next root before its own dispatch accounting finishes. The report includes the observed counters and a bounded event trace.

The [mixed scheduler contract](../docs/reconstruction/MIXED_SCHEDULER_IMPLEMENTATION.md) distinguishes range, one-shot callback, immediate terminal and conditional jobs. This is a standalone executable reference; optional gameplay integration is described below. Native threads, queue priorities, platform event operations and original-game stepping remain outside its validation.

## Gameplay with job traces

Use `python3 -m engine.cli --scenario engine/examples/mixed_gameplay.json --ticks 120` for a headless run, or add `--serve --port 8770` to inspect that scenario locally. Its `execution_mode: mixed` runs actual gameplay phases through the scheduler and emits `gameplay_job` records into `/trace`. The direct path remains the default for other scenarios.

Run `python3 -m engine.examples.gameplay_scheduler_probe` to compare direct and mixed state, event, replay and checkpoint behavior under changing frame intervals. See the [integration contract](../docs/reconstruction/GAMEPLAY_JOB_INTEGRATION.md) for the designed graph and rollback boundary.

## Trace analysis

`GET /trace/analysis` reads the retained trace without advancing simulation. It correlates frame and substep attempts, phase entry/return evidence, commits and rollbacks. Dropped records make the report incomplete; an outer-frame abort invalidates earlier local substep commits. A complete report describes available evidence and can include failed execution attempts. See the [analysis contract](../docs/reconstruction/TRACE_ANALYSIS.md).


### Paused tuning and animation resource replacement

`SchedulerController` now exposes mutations through the same exclusive gate as
stepping. These are designed APIs for the independent engine. They do not call the
original game's loading thread or establish a native hot-reload contract.

```python
from engine.control import SchedulerController
from engine.animation import default_resources

controller = SchedulerController({'execution_mode': 'mixed'})
token = controller.pause()
token = controller.tune(token, {'physics': {'brake_deceleration': 4}})
rig, clips = default_resources()  # synthetic fixtures
token = controller.replace_resources(token, {
    'category': 'synthetic', 'rig': rig, 'clips': clips,
})
result = controller.step_once(token, {'steer': 0.2})
controller.resume(token)
```

Each successful mutation returns a fresh pause token and invalidates the old one.
Validation runs against an isolated candidate. Failure preserves the published
engine, replay segment, controller generation and current token. Mutation does not
advance the published tick or body. Tuning performs the engine's isolated next-tick
validation; resource replacement resets visual clocks according to the existing
resource contract. Both start checkpoint-based replay segments that retain the
new scenario/resource content.

The controller must exclusively own its engine. Direct engine calls and the
legacy HTTP inspector's direct-engine API do not acquire these pause-token
contracts. Callback side effects outside the owned engine remain outside rollback.


### Controller JSON API

Run `python3 -m engine.control_server --port 8771` for a separate loopback-only
controller service. It owns its engine exclusively and does not expose the legacy
inspector's direct-engine mutation routes. No browser or original game is needed.

Read-only routes are `GET /state`, `/checkpoint`, `/replay`, `/trace` and
`/trace/analysis`. Submit JSON to `POST /command`. Successful commands return
`{snapshot, token}`; retain the returned token after pause, reset, restore, tuning
or resource replacement. Resume and ordinary frame submission return a null token.
A step returns the same still-valid token.

| Operation | Additional JSON fields |
| --- | --- |
| `pause` | none |
| `resume` | `token` |
| `step_once` | `token`, optional `actions` |
| `step_frame_once` | `token`, `dt`, optional `actions` |
| `submit_frame` | `dt`, optional `actions`; requires open submission gate |
| `tune` | `token`, `changes` |
| `replace_resources` | `token`, `bundle` |
| `reset` | optional `scenario`; returns a fresh paused token |
| `restore` | `checkpoint` previously read from this controller API |

`dt` is bounded to zero through one second per HTTP request. Request bodies are
bounded to two million bytes. Mutation requests with a foreign browser Origin are
rejected. Tokens enforce controller identity/generation, not authentication.
The service is for trusted local scripts. A single request dispatcher preserves
command/response ordering.

Invalid commands return HTTP 400 with an error and current controller snapshot.
An execution failure can close the gate and invalidate a token according to the
controller contract; call `pause` to obtain the current token after inspecting the
incident. Invalid mutation validation preserves the old token. HTTP 403 denotes
a rejected Origin, and 404 an unknown route. Snapshot control scope explicitly
states that this is the owned engine, not native game control.


### Repeatable HTTP tuning comparison

With the controller service running, execute:

```sh
python3 -m engine.examples.controller_experiment --url http://127.0.0.1:8771 --output /tmp/brake-comparison.json
```

This example **resets the addressed independent runtime**. It runs a scripted turn,
saves a checkpoint, then restores that same checkpoint for gentle and strong brake
tunings. Inputs precede explicitly requested simulation frames, so network delays
do not define input duration. The default is 30 frames per segment at 1/60 second;
`--frames` accepts 1 through 240.

The report retains the approach and both branches, including body samples, input
generations, the starting checkpoint, replay recordings, replay equality, traces
and trace-analysis reports. Each branch is saved before restoring another one.
Compare results by their recorded simulation time/tick, not HTTP response timing.
The service stays paused when the example completes normally.

The CLI exits with status two when replay equality or trace completeness fails,
after writing the report. Request/connection errors propagate; a partially executed
remote command must not be blindly retried after a network timeout. The example
uses synthetic world and resources and tests only the independent engine.


For detailed physics-to-animation inspection, configure
`"trace": {"capacity": 16000, "capture_phase_state": true}` in the scenario.
The trace then includes copied phase entry/return state, input generation and full
owned animation pose. See [phase capture](../docs/reconstruction/TRACE_ANALYSIS.md#optional-phase-state-capture)
for abort and capacity interpretation.


For standalone recovered animation binding helpers and synthetic examples, see
[the binding inspection API](../docs/reconstruction/ANIMATION_BINDING_API.md).
These helpers require caller-supplied mapping data and are not a complete rig loader.

[Animation endpoint motion](../docs/reconstruction/ANIMATION_ENDPOINT_MOTION.md)
provides displacement and relative-rotation arithmetic over supplied samples,
with an explicit reciprocal-square-root seed policy.

[Animation sampling dispatch](../docs/reconstruction/ANIMATION_SAMPLING_DISPATCH.md)
provides an adapter for recursive resource routing and caller-supplied decoders,
including shared output and hint/cursor state.

[Byte-time key selection](../docs/reconstruction/ANIMATION_KEY_SELECTION.md)
implements cached forward lookup and rewind binary search over supplied ticks.

[Encoding-zero channel decoder](../docs/reconstruction/ANIMATION_QUATERNION_SAMPLER.md)
connects supplied channel bytes to quaternion output and supports the recovered
resource-dispatch callback interface. Other encoding IDs are rejected.

The shared `registered_channel_decoder` additionally supports
[encoding-27 vector channels](../docs/reconstruction/ANIMATION_VECTOR_SAMPLER.md).
Its private-corpus comparison is limited to reserialized decoded keys.

[Corpus inspection](../docs/reconstruction/ANIMATION_CORPUS_INSPECTION.md) provides
`python3 -m engine.animation_corpus` for caller-owned clip bodies and track-boundary
metadata. It reports unsupported formats and emits aggregate diagnostics only.

Runtime descriptor addressing is exposed by [`animation_outputs`](../docs/reconstruction/ANIMATION_OUTPUT_API.md), with distinct scalar/timeline storage and explicit owner evaluation. Authored-to-runtime lowering remains open.

Runtime class-0 identity lookup and compile dependencies are available through [`animation_identity`](../docs/reconstruction/ANIMATION_IDENTITY_API.md). Original map population and parameter freshness remain open.

Lazy parameter preparation and explicit reset boundaries are exposed by [`animation_parameters`](../docs/reconstruction/ANIMATION_PARAMETER_LIFECYCLE.md). Reset placement is recovered within one update routine; scheduler cadence remains open.

The recovered local animation deferral gate and float32 interval accumulation are exposed by [`animation_update_policy`](../docs/reconstruction/ANIMATION_UPDATE_POLICY.md). Caller scheduling and live configuration remain unresolved.

The named threshold callback's packet arithmetic is exposed by [`animation_thresholds`](../docs/reconstruction/ANIMATION_THRESHOLD_PRODUCER.md), including its direct deferral-policy join. Native component resolution remains external.

[`animation_component_clock`](../docs/reconstruction/ANIMATION_COMPONENT_DISPATCH.md) selects the recovered component interval source and exposes local interface-call gates. The component/factory join is static; live scheduler membership remains open.
