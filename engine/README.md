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

For recovered bank/context transform math, run the separate [animation work-transform testbench](../docs/reconstruction/ANIMATION_WORKBENCH.md). It accepts JSON and requires no game process.

## macOS native-test SDK mismatch

Some tests compile authored C fixtures. If they fail with `tapi error: malformed
file` and `unknown architecture` in `libSystem.tbd`, check that the compiler and
SDK come from compatible installations. A tested failure used the selected
Xcode compiler with a newer Command Line Tools SDK. It was a build-environment
failure, not a fixture assertion failure.

When `xcode-select -p` points to a full Xcode installation with a bundled macOS
SDK, this command selects that SDK for the test process and its compiler children:

```sh
SDKROOT="$(xcode-select -p)/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk" \
  python3 -m unittest discover -s tests
```

This does not change the global developer directory. Verify the SDK directory
exists first; the path layout is not valid for a Command Line Tools-only selection.
Do not hide compiler failures by skipping the native fixtures.

## Animation bank JSON testbench

Run the recovered mixed-channel and supplemental evaluator without a game process:

```sh
python3 -m engine.animation_bank_bench engine/examples/animation_bank_input.json
```

The example contains synthetic receipt inputs. Each case supplies `inputs` for
`evaluate_numeric_pose_bank` and an explicit `seed_policy`. `recorded` requires
ordered `normalization` entries with matching `length` and `seed`; missing, extra
or mismatched entries fail. `authored_exact_sqrt` requires no observations and
uses a labeled mathematical substitute, not native approximation equivalence.
Output includes the input hash, route, channels, supplemental records, status
and normalization trace. Use `--output result.json` to save it. Cases are
independent, not consecutive game frames. Supported domain is selector 2,
modes 0/4 and numeric kinds 1/5/6 with separate supplied storage. Optional
`group_mask`, `groups` and `range_selector` select a descriptor subrange; output
reports the range and absolute processed indices. Set case `entry` to
`group_wrapper` and supply `group_count` to expand masks into sequential calls;
the default `inner` entry retains its single-range semantics.
See [the integration evidence](../docs/reconstruction/CENTRAL_IMPULSE.md#mixed-channels-with-supplemental-evaluation).

## Input refresh JSON testbench

```sh
python3 -m engine.input_refresh_bench engine/examples/input_refresh_plan.json
python3 -m engine.input_refresh_bench engine/examples/input_refresh_plan.json --output /tmp/input-refresh.json
```

`inspect_timeline(plan)` in `engine.input_refresh_bench` accepts the same JSON
object with an `events` list. `publish` supplies two four-lane vectors, 32 scalar
channels and an opaque uint64 `now`. `refresh` supplies uint32 `source_kind` and
`lane_mode`, explicit boolean owner/configuration/ownership/cache-mask gates,
and `processor: "bypass"` or `"default"`. The checked-in example lists the exact
field names. Default explicitly selects the decoded copy processor; it is never
inferred from missing configuration. Its first-use flag and stored vector persist
across events and appear in each observation. Suppression, missing source
configuration and bypass leave this state unchanged. This caller selection does
not prove which processor the native player uses. The lower-level vector adapter
accepts other explicit processor callbacks.

Output includes an input hash, event indices, action raw/sample/direction/status,
cache clock, derived press stamps and evaluation diagnostics. Events operate on
synthetic zero-initialized caches and action state. Publication events do not
refresh the action automatically. Suppression can clear samples while retaining
prior status, whereas an evaluated masked zero updates status to zero. Direction
uses the labeled scalar reciprocal-seed approximation.

This is a detached inspection API, not a native mod command. Event indices are
harness labels, not engine requests or sample generations; clocks are not seconds.
See [input-route evidence and boundaries](../docs/reconstruction/INPUT_TO_ACTION_ROUTE.md).

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

The selected animation-time visitor is available as [`animation_batch`](../docs/reconstruction/ANIMATION_BATCH_BINDING.md), preserving per-batch callback capture and reverse local receiver order. Native membership and cross-job ordering remain open.

[`animation_membership`](../docs/reconstruction/ANIMATION_MEMBERSHIP_COPY.md) models the pre-action gather task's source-registry copy into that job. It preserves capacity and inactive entries on reuse, and preserves the existing active count when the source is empty. Registry policy and cross-request ordering remain open.

Its [`claim` API](../docs/reconstruction/ANIMATION_CLAIM_LIFECYCLE.md) consumes the remaining count before returning a span for visitation. Zero means no unclaimed entries, not that callbacks have returned. Original worker/visitor composition has been checked with synthetic receivers; live and exceptional-mode storage exclusion remain unverified.

The [animation-stage probe](../docs/reconstruction/ANIMATION_STAGE_DEPENDENCIES.md) runs a recovered seven-job dependency slice through the mixed scheduler. It demonstrates the action gather retaining its hold until animation dispatches finish, using explicit synthetic receiver lists and no-op bodies.

[`event_registry`](../docs/reconstruction/ANIMATION_EVENT_REGISTRY.md) provides 53 serial token lists with exact-identity duplicate suppression and last-entry replacement on removal. Slot 16 supplies the animation-time source. Component-specific activation and live player membership are not established by this API.

[`kino_event_routes`](../docs/reconstruction/KINO_EVENT_ROUTES.md) exposes the constructor-installed KinoComponent slot-16 route and secondary slot-22/23 selection from owning-object mode bits. Context lookup and lifecycle invocation remain caller-supplied evidence.

[`kino_activation`](../docs/reconstruction/KINO_ACTIVATION.md) produces the direct activation routine's ordered registry/helper effects and resulting flags. It distinguishes context-group coverage from slot-16 insertion and preserves active state on the inspected missing-world branch. External helper effects remain explicit and unimplemented by this planner.

### Ordinary animation operation testbench

Run the complete reconstructed ordinary operation against supplied synthetic data:

```sh
python3 -m engine.animation_operation_bench engine/examples/animation_operation_input.json --output /tmp/animation-operation-result.json
```

The `animation-operation-bench-v1` document contains 1..64 `cases`. Each case
supplies `inputs` for `evaluate_ordinary_pose_operation`, an optional `label`, and
an explicit `math_policy`. The example uses synthetic inputs and observations
from the mixed-operation emulation receipt, not game assets or a live recording.

- `recorded` requires ordered `services` entries with `service`, `input`, `output`
  and `normalizations` entries with `length`, `seed`. Missing, mismatched and unused
  entries fail. It reproduces supplied numerical observations without guessing.
- `authored_host_math` uses host acos/sin and an exact reciprocal-square-root seed
  rounded to float32. Both recording lists must be empty. This is an authored
  numerical policy and does not establish original instruction equivalence.

Inputs name banks by logical identities; each bank includes numeric `channels`,
supplemental `records`, auxiliary `poses`/`weights`, `flags`, `supplemental_mask`
and `supplemental_counter`. Source identities can coincide. Destination must be
distinct. Operation routing and stable group metadata are supplied explicitly,
as are component-derived flags and keyed lookup results. No binary addresses,
assets, DLL, game launch or live process access are needed.

Output includes an input SHA-256, selected math policy, consumed numerical trace,
route, group calls, completion mask, updated banks, manager entry masks and reset
effects. Reset effects describe reconstructed state changes; they do not free
native storage. An ordinary entry rejects the special route; destination aliases fail explicitly. See
[operation evidence and limits](../docs/reconstruction/CENTRAL_IMPULSE.md#ordinary-pose-operation-composition).


For the Hermite branch set a case's `entry` to `special`. Supply `descriptors`
as key/type pairs, `total_end`, `groups`, `first_tangents`, `second_tangents` and
`tangent_scale` instead of `kinds` and `group_count`. Each tangent record has
four-lane `vector` and `rotation` fields. The operation must select the special
route; tangent data is supplied, not generated from an assumed timestep.
[Special-operation evidence](../docs/reconstruction/CENTRAL_IMPULSE.md#complete-special-pose-operation)
includes the zero-mask behavior that differs from an ordinary no-op expectation.

### Composed player animation observation

`engine.player_animation_observation.capture_player_animation(readv, entity,
image_base, keys, guards, profile, record_count=None)` combines the existing
skeleton binder and pose-interval reader. The caller supplies a freshly verified
entity, build-specific profile, process-identity guards and bounded read transport.
It does not acquire a player or access a process by itself.

The function requires one exact SkeletonComponent with a matching owner backlink,
retains component-array/slot/type/owner guards across the pose read, and rechecks
binding facts afterward. Pose metadata bounds and bank-selection/epoch endpoints
are checked by the existing reader. Output includes address-free binding facts,
requested channel values, missing-key reports and explicit consistency limits.

This is an adapter-facing Python API, not yet a native loader command. Matching
reads do not pin object lifetime, exclude ABA changes or establish animation
completion. `suitable_for_animation_writes` remains false. Captured pose values
must stay private; public fixtures use synthetic memory only. A read-only loader
binding still needs process transport integration and a bounded live validation.

Spawn publication can be inspected offline with explicit parent snapshots and
reciprocal-square-root estimates:

```sh
python3 -m engine.spawn_publication_bench --request engine/examples/spawn_publication_input.json
```

This carries supplied animation-bank state across frames and reports matrix
outputs and reset order. It records entity publication without accessing the game.
See the [input contract and limits](../docs/reconstruction/CENTRAL_IMPULSE.md#offline-spawn-sequence-inspection-command).


## Inspect animation bank ownership sequences

```sh
python3 -m engine.animation_pool_session engine/examples/animation_pool_input.json
```

This offline runner reports reuse, allocation misses, release and wrapper cleanup
with state after each operation. Pose copying and storage services are explicitly
recorded without execution in JSON mode. Python callers may supply implementations.
See the [session contract](../docs/reconstruction/ANIMATION_POOL_SESSION.md).


## Regular byte-bank inspection

The existing bank testbench also accepts `entry: "regular_bytes"`:

```sh
python3 -m engine.animation_bank_bench engine/examples/animation_byte_bank_input.json --output /tmp/animation-byte-bank.json
```

The example is a synthetic mixed-channel bank with a quaternion channel and a
supplemental rotation. It uses recorded emulator normalization seeds, reproducing
one public joined instruction case. No game assets or process are needed.

Inputs include three separate banks (`destination`, `first`, `second`), each with
integer-byte `data`, `profile` metadata and explicit `records`. The destination
also supplies `flags`. Profile metadata contains channel descriptors, group count,
channel count and group words. Operation fields are `weight`, `selector`,
`request_mask`, and optional `exclusion_mask`. See the complete example for shape.

Results contain output bytes, flags, supplemental records, selected ranges,
normalization trace and input SHA-256. Each case retains its explicit seed-policy
label. `recorded` checks every normalization input and consumes every supplied seed;
`authored_exact_sqrt` is a mathematical inspection policy, not native RSQRT parity.
Neither policy proves original clip selection or full engine equivalence. The JSON
boundary clones inputs and supports separate banks only. Limits are 1 MiB per bank,
4096 descriptors and 255 supplemental records. Partial aliasing, masked/additive
wrapper variants and native allocation/scheduling remain outside this command.

### Masked animation byte-bank bench

Run the synthetic masked-bank example without the game or private analysis files:

```sh
python3 -m engine.animation_bank_bench engine/examples/animation_masked_bank_input.json --output /tmp/animation-masked-bank-result.json
```

The `masked_bytes` entry accepts the same three separate byte banks as
`regular_bytes`, plus `weight_mode` (0 or 1) and `uniform_groups` (uint16).
Descriptors also require uint32 `key` values for the recovered keyed weight
walk. The example compares partial-mask uniform overrides with a full-mask
request that ignores those overrides. Results include output bytes, flags,
supplemental records, visited group modes and an input hash.

Normalization policy remains explicit: `recorded` checks every supplied input
and seed; `authored_exact_sqrt` is a labeled approximation substitute. The example
has identity supplemental rotations and needs no normalization observations.
The JSON boundary deep-copies inputs and represents separate banks only; it does
not encode in-place aliases. This entry exercises bank kernels, not the outer
pose wrapper or live animation selection. See the
[masked output evidence](../docs/reconstruction/CENTRAL_IMPULSE.md#masked-bank-blend-output).

For a nonidentity quaternion channel plus repeated supplemental rotation blending:

```sh
python3 -m engine.animation_bank_bench engine/examples/animation_masked_rotation_input.json --output /tmp/animation-masked-rotation-result.json
```

This fixture supplies recorded normalization inputs/seeds. Changing inputs may
invalidate those observations; the bench refuses mismatched or unused records.
See [masked rotation validation](../docs/reconstruction/CENTRAL_IMPULSE.md#masked-rotation-output-validation).

### Paused brake/boost mod

Run the independent-engine example with no game installation:

```sh
python3 -m engine.examples.speed_mod_demo
```

It applies +2/-2 speed pulses at a held tick, single-steps, resumes, advances one
second, and checks the exported replay's final state hash. Resources are synthetic.

`SchedulerController.adjust_speed(token, delta_speed)` is also exposed by
`python3 -m engine.control_server` at `POST /command`:

```json
{"op":"adjust_speed","token":{"controller_id":"<from pause response>","generation":0,"pause_serial":0},"delta_speed":2}
```

Use the complete token returned by `pause` or a preceding mutation; the numbers
above are placeholders. Success returns a fresh token for the next mutation,
step, or resume. Failed validation leaves state and the current token unchanged.

This is an authored independent-engine mod policy, using the native host's
bounded pulse convention: finite nonzero delta within -10..10, direction from
current three-dimensional velocity, direction unresolved below speed 0.5,
nonnegative brake target, boost capped at 60 and refused at/above 60. These are
API limits, not recovered physical constants. Unlike the private game setter,
this operation preserves angular velocity and therefore does not reject spinning
bodies. It leaves positions, pose/animation clocks, scheduler state and tick
unchanged. The ordinary next physics tick can change velocity through contact.

Successful mutation appends an `adjust_speed` replay command and records a
`mod_speed_adjusted` event with before/target speeds and evidence category.
Replay executes speed pulses in their original command order, preserving preceding
inputs and steps in the current replay segment. Explicit restore, tuning and
resource replacement may still establish a checkpoint base. This does not prove
original-game determinism.

### Recovered byte-bank blending in the running pose graph

```sh
python3 -m engine.cli --scenario engine/examples/byte_pose_graph.json --ticks 120 --output /tmp/byte-pose-replay.json
python3 -m engine.cli --replay /tmp/byte-pose-replay.json
```

The explicit `byte_blend` graph node accepts `base`, `overlay`, scalar `weight`,
and required `normalization: "authored_exact_sqrt"`. Both children must have the
same pose space. It packs their sampled poses into float32 banks and executes
`reference.animation_bank_blend.blend_regular_pose_bank`, including its near-one
copy branch, typed arithmetic and quaternion path. Model-pose composition then
uses the resulting local pose in the normal engine animation phase.

`engine/pose_bank_adapter.py` defines an authored 32-byte-per-bone layout: kind 5
for translation padded with a zero fourth lane, kind 6 for XYZW rotation. It uses
full-mask traversal, distinct bank storage and empty supplemental record lists.
This mapping is not a decoded original-rider descriptor table. Normalization uses
an explicitly selected exact-square-root seed, not a recovered hardware RSQRT
seed. Inputs are limited to 2048 bones by the descriptor's uint16 offset range.
Existing graph nodes retain their previous arithmetic. Diagnostics expose the
bank branch visits, destination flags, mapping and normalization policy.

The supplied scene uses synthetic clips. Tests cover float32 translation,
nonidentity rotation, copy routing, input isolation, inactive-node validation,
and runtime replay/checkpoint continuation. They establish integration of the
recovered kernel under these choices, not original rider animation fidelity.

The same scene now adds a `byte_additive` node above the regular blend. This node
requires `base` in local space and `delta` in delta space, plus explicit `weight`
and the same normalization policy. The adapter sets `swap=True` on the recovered
bank router to put base first and delta second; native default ordering would
reverse them. Kind-5 translations add weighted delta lanes. Quaternion and
near-one unweighted-combine branches remain those of the recovered router.
Diagnostics identify the operation, source ordering and branch visits. This
connects the recovered arithmetic to synthetic lean layering; it does not identify
original trick, landing or locomotion graph selection.

`byte_mask` adds recovered keyed weight-byte traversal to this graph path. It
requires local/delta space agreement between `base` and `overlay`, an explicit
`weight`, normalization policy, and `bytes` mapping bone names to 0..255. Missing
bone names receive zero; unknown names are reported in `unmatched_mask_bones`.
Invalid bytes are rejected even in inactive nodes. No original bone mask is
inferred from a name.

Its authored layout uses 36 bytes per bone, with a weight byte after the eight
float lanes. Descriptor order is translation, paired same-key weight byte, then
same-key rotation. The recovered keyed walker consumes the byte and reuses its
weight for rotation. Full-mask mode reads the overlay bank's bytes; no uniform
group override is applied. The layout allows at most 1820 bones. Zero mask weight
removes the overlay contribution but does not bypass the recovered rotation
normalization path, so bitwise identity for arbitrary nonunit inputs is not
promised. Tests cover 0/128/255 masks, rotation weight reuse, invalid bytes,
unmatched names and complete engine replay. The sample scene combines all three
byte-bank node types using synthetic clips and an authored partial-root/full-knee mask.

### Combined control, physics and animation experiment

```sh
python3 -m engine.examples.gameplay_mod_experiment --output /tmp/gameplay-mod-experiment.json
```

This bounded headless experiment combines mixed job dispatch, unequal outer-frame
intervals, steering, jump charge/release, flip input, braking and two paused speed
pulses with all three recovered byte-bank graph nodes. Graph weights consume the
jump and lean controls; the controls-to-graph selection remains authored. It
records per-frame body/pose/input samples, events, scheduler trace and a complete
replay, then verifies both final state and event equality by replaying it. Names
such as `release` and `settle` label commanded segments, not proof that a specific
original-game trick or landing occurred. The fixture uses synthetic rig/clips.

The command exits nonzero for replay disagreement, trace truncation or incidents.
It can be slower than a plain engine run because the controller snapshots and
copies the accumulated trace at transaction boundaries. It does not run the game
or claim native timing, collision, landing or animation parity.

For per-frame scripted observation, `SchedulerController.snapshot`,
`submit_frame`, `step_once` and `step_frame_once` accept keyword-only
`include_trace=False`. Defaults retain the complete snapshot API. The lighter
response omits `trace` and instead supplies `trace_summary` with attempted,
retained and dropped counts, completeness, and `records_included:false`.
Numerical state remains a detached copy. This option changes observation cost
only: trace capture, rollback copies, pause exclusion and replay stay active.
Invalid non-Boolean options fail before input or execution changes. Fetch one
full snapshot or checkpoint when the accumulated records are needed. The combined
experiment uses this path for samples and retains the full final trace.

HTTP clients can request the same lighter response with
`GET /state?trace=summary` or `"include_trace":false` on `POST /command`.
The command option is Boolean and validated before dispatch, so malformed options
cannot advance the simulation. Failed commands honor a valid summary selection.
`GET /trace` and `/checkpoint` retain their complete-record interfaces; ordinary
`GET /state` and commands without this option retain their existing response
shape. The HTTP comparison experiment now requests summary responses during its
frame loop and fetches complete traces at experiment boundaries.

Use `--physics-mode rigid_cells --sport snowboard` (or `--sport ski`) on the
combined experiment to exercise recovered tetrahedral pressure/contact kernels
with the graph and speed-mod API. Each sample now includes physics diagnostics,
so impulse activity, immersion and authored contact policies remain inspectable.
The box hull, force weighting, steering/jump rules, substrate and integration are
still synthetic policies documented in `engine/rigid.py`; this mode does not
establish a reconstructed original constraint solver.

A 444-tick snowboard run retained all 225 samples and the complete scheduler
trace. Final state and events replayed exactly, with no incidents. It recorded
184 contact-pressure samples, immersion from 0 to approximately 0.448, one jump
and one landing event in this model. Short ski/snowboard tests also verify that
a paused speed pulse preserves stored rigid angular momentum and the current
pose before the next physics tick. These results establish system integration,
not matching original ski/snowboard feel or landing classification.

### Paused central impulse

`SchedulerController.apply_central_impulse(token, [jx, jy, jz])` exposes the
recovered float32 `velocity += inverse_mass * impulse` arithmetic on the independent
engine's single body. HTTP `/command` accepts `op: "apply_central_impulse"`, the
pause token, and `impulse`. Success returns a fresh token and records the command
for replay; invalid input leaves the published state and token unchanged.

The adapter uses the scenario body's positive mass, dynamic/unsuppressed descriptor
policy and no backend dispatch. These are explicit independent-engine choices.
It preserves angular velocity, rigid angular momentum, pose and clocks. It does
not simulate a separate coupled rider, original runtime locking, or native callback
scheduling. Impulse is applied once, with no extra timestep multiplier. This is
separate from the live host's speed setter, which resets spin. Evidence:
[central impulse contract](../docs/reconstruction/CENTRAL_IMPULSE.md#recovered-routine-contract).

## Snow jump inspection bench

```sh
python3 -m engine.snow_jump_bench engine/examples/snow_jump_input.json --output /tmp/snow-jump-result.json
```

This offline bench composes the recovered compiled-curve evaluator, stateful
jump branch and central-impulse arithmetic. It reports per-update gains, branch,
scalar state, ordered body requests and before/after linear and angular values.
The example is explicitly authored synthetic data, not an extracted profile.

Provide initial cached factor/countdown, one main body and optional rider body,
three sampled curves, configuration masses/base/gravity, and a sequence of
elapsed interval, release signal, air time, contact depth and projected speed.
Combined mass is supplied explicitly; the bench does not infer it from profile
rider mass. Curves are compiled once and evaluated for inspection on each row;
those diagnostic evaluations do not assert that the original branch visited them.

The bench applies requests serially to its own body dictionaries, preserving
float32 ordering and suppression gates. It does not integrate gravity, solve
contacts/constraints, generate release signals, animate a rider, or call backend
dispatch. Spin preservation here covers central arithmetic only. The browser
prototype retains its labeled synthetic jump policy; this bench does not silently
replace that policy or invent missing live profile selection.

See the [stateful jump evidence](../docs/reconstruction/CENTRAL_IMPULSE.md#stateful-jump-consumer)
and [instruction comparison](../native/snow_host/jump_branch_validation.json).

To include the recovered charge-release state transitions:

```sh
python3 -m engine.snow_jump_bench engine/examples/snow_release_jump_input.json --output /tmp/snow-release-jump-result.json
```

This authored example supplies remapped raw input and cooked coil samples. The
bench computes saved charge, elapsed release time, rate and one-update release
signals before evaluating jump curves. It uses separate elapsed and derivative
intervals. Provide `release_state`, a configuration `release_threshold`, and each
frame's `cooked`, `raw_remapped_charge`, `derivative_dt` and `input_update_mode`.
Do not also provide `release_signal`; the bench rejects that ambiguity. Trace
rows expose before/after release state. Device remapping, cooker output and mode
selection remain supplied inputs. This addition has synthetic boundary and
composition tests, not a new original-instruction or live input-ingestion proof.

The release-state kernel subsequently passed an
[original-instruction comparison](../native/snow_host/charge_release_validation.json)
with 1,536 exact cases, including unequal timing arguments. This strengthens the
kernel evidence; the surrounding authored bench and its supplied cooked samples
remain distinct from original input-service behavior.


### Cooker through jump impulse

```sh
python3 -m engine.snow_jump_bench engine/examples/snow_cooker_jump_input.json --output /tmp/snow-cooker-jump-result.json
```

The optional `cooker` block adds recovered float32 input filtering before charge
release, jump curves and central impulse arithmetic. It requires `release_state`,
four named `coefficients`, `epsilon`, and a `decay` block containing 257 explicit
`samples`, `low`, `high`, `padding` and `provenance: authored_synthetic`. Each frame
supplies `cooker_target` and a positive `cooker_dt`; it must omit `cooked` and
`release_signal`. Targets and remapped raw charge remain separate caller inputs.

Each trace row reports the cooker direction, lookup argument, lookup result,
step and final value alongside release state, jump branch and body changes.
The example intentionally uses a constant-one synthetic lookup and base damping
25 to make the cooked sequence 0.25, 0.5, 0.25, 0, 0. Raw release on the third
frame triggers an impulse on the fourth. The fifth is suppressed by cooldown.
This fixture is a diagnostic, not a realistic decay curve or game tuning.

`cooker_dt`, `elapsed_dt` and `derivative_dt` are independent supplied clocks.
The serial orchestration is authored and does not establish their relationship
in the original scheduler. Native exponential sample generation, device mapping,
contact dynamics and animation remain outside this bench. Existing scenarios
with supplied cooked values or supplied release signals retain their behavior.


To use the instruction-validated default decay table instead of synthetic samples:

```sh
python3 -m engine.snow_jump_bench engine/examples/snow_reconstructed_cooker_jump_input.json --output /tmp/snow-reconstructed-cooker-jump-result.json
```

Set `cooker.decay` to exactly `{"mode":"reconstructed_default",
"vector_path":"sse2","scalar_path":"sse2"}`. The vector path may also be
`sse41`. Scalar FMA is rejected because the private emulator cannot execute its
fused instruction. Paths are explicit scenario choices; the bench does not infer
the running game's CPU dispatch. This mode computes the original default table
from reconstructed arithmetic and mathematically generated mantissas.
`decay_configuration` in the result records the selection. Supplied-sample mode
remains available. The new example submits on frame five and enters cooldown on
frame six; its coefficients and scenario are still authored synthetic data.


Ground-sport steering now uses `reference.input_cooker` and the reconstructed
default SSE decay table. This replaces the earlier double-precision filter in
`engine.physics`; small trajectory/hash changes relative to older versions are
expected. The fixed CPU path is a reconstruction choice. The coefficients,
control cadence and turn policy remain synthetic. Physics diagnostics include
`steering_cooker` with direction, lookup argument/result, step and final value.
Old checkpoints retain their stored steering value and continue with the new
arithmetic; reproducing an older version's exact trajectory requires that version.

Input-profile speed now projects body velocity against the sampled terrain normal
with recovered float32 arithmetic. Diagnostics include `input_speed`. The normal
source and sampling time remain authored, especially while airborne; this is not
proof of original cached-normal behavior. Vertical flight over flat terrain no
longer selects the fast input profile solely because of vertical speed.

The input projection normal is now cached in `_snow_physics.projection_normal`.
Supported updates replace it with sampled terrain; unsupported updates retain
it. This follows the recovered retention behavior but uses support as a proxy
for native positive immersion and omits native candidate fitting/smoothing.
Missing checkpoint state and airborne spawns use a synthetic world-up seed.
`input_speed.projection_normal` and `normal_update` expose these choices.

The jump bench can derive its air clock: add `contact_state` containing
`air_time` and `contact_time`, then replace each frame's `air_time` with supplied
`immersion`. The recovered clock clears immersion/contact time at immersion <=
float32(.001), otherwise clears air time and advances contact time. Trace rows
include before/after contact state and the result includes `final_contact_state`.
Explicit `air_time` alongside `contact_state` is rejected. Immersion geometry is
still external; a synthetic contact flag is not silently converted into volume.

### Motion input shared across a physics batch

`motion_input_batch.prepare_motion_input_batch` composes the recovered ingestion
prefix with a caller-supplied scheduler plan. The caller resolves the ingestion,
alternate-action and X-sign gates and supplies the smoothing coefficient. Four
action reads occur in recovered order, including separate reads of repeated
IDs. `batch.execute(update)` supplies the same immutable ingestion result to
each physics callback. A changed source is read at the next eligible preparation.

```python
from engine.motion_input_ingestion import ingest_motion_prefix
from engine.motion_input_batch import prepare_motion_input_batch
from engine.scheduler import schedule

zero = bytes(16)
previous = ingest_motion_prefix((zero,) * 4, flip_x=False,
    counts=(0, 0), smoothed=(zero, zero), alpha=0.5)
steps = schedule({}, 0.05, {'mode': 'fixed', 'fixed_dt': 0.01})
batch = prepare_motion_input_batch(previous, steps,
    ingestion_enabled=True, read_action=lambda action_id: zero,
    alternate_enabled=False, actor_predicate=False, flip_x=False, alpha=0.5)
observed = []
batch.execute(lambda ordinal, elapsed, derivative, motion:
    observed.append((ordinal, motion.primary_count)))
assert observed == [(i, 0) for i in range(5)]
```

This example is synthetic. The API's batch composition is supported by the
[live BeforeSimulation observation](../native/snow_host/before_input_boundary_live.json),
not established for every mode. Gate selection and numerical ingestion rules
remain separate. The interface does not replace the browser runtime's authored
control mapping, invoke original-game functions, or implement the physics solver.
A caller-requested zero-step batch still refreshes eligible input; this is an
explicit interface choice without a corresponding live zero-step observation.
Suppression preserves prior state without action reads. Callback failures stop
execution and propagate; earlier callback side effects are not rolled back.

For the recovered activity/controller/motion-enable/skip decision, use
`motion_input_gate.resolve_motion_input_gate(read_flag, predicate_a, predicate_b,
prepare_a, prepare_b)` and pass its `ingestion_enabled` result into batch
preparation. `read_flag` receives the names `active`, `controller_blocked`,
`motion_enabled`, and `skip_ingestion`; it must read caller-owned state at call
time, not return a snapshot taken before preparation. Predicate A takes
precedence over B. The chosen preparation runs before the skip flag is read.

This gate kernel matched all 192 original-instruction emulation cases, including
predicate/preparation call order. Helper bodies were substituted; synthetic
preparation changes to skip test sensitivity rather than establish those
helpers' real effects. Actor preparation before these gates, controller handle
resolution, and downstream bookkeeping remain caller dependencies. A failed
outer gate prevents subsequent reads and preparations. Unresolved/non-boolean
values raise an error rather than silently disable ingestion.

For the inspected concrete actor type, preparation predicates can be supplied
as `lambda: preparation_mode_matches(read_actor_mode(), 'a')` and the equivalent
`'b'` call from `engine.motion_input_gate`. They compare raw modes 9 and 5,
respectively. These are build-qualified mode values, not portable sport IDs.
Other modes skip both preparations but may still ingest. The predicates are
validated leaves; preparation bodies remain caller-supplied dependencies.

`physics_timing_observation.observe_physics_timing(read, owner, physics_manager,
policy_address)` provides a bounded inspection API for the recovered timing
state and smoothing ring. The caller supplies an exact read transport and fresh
build/process/owner qualification. It performs no process access on its own.
Use its explicit status rather than treating missing or unstable state as zeros.
Returned runtime addresses belong in private evidence, not public reports.
See [reader contract](../docs/reconstruction/SCHEDULER_SMOOTHING_AUDIT.md#bounded-timing-state-reader).

## Detached command-manager initialization

Run `python3 -m engine.examples.command_initialization_probe` for recovered
constructor writes and normal-return publication with supplied synthetic services.
[command_initialization.py](command_initialization.py) accepts caller-owned storage
and explicit lock, container, allocation and cleanup callbacks. It preserves
unwritten bytes, models four backing-allocation requests and publishes only after
normal constructor return. It does not allocate the manager itself or access the
live game. See [the lifecycle evidence](../docs/reconstruction/REQUEST_COMMAND_LIFECYCLE.md#constructor-return-publication)
for the 96-case byte comparison and unresolved ownership boundaries.

For the preceding storage request and null-result branch, run
`python3 -m engine.examples.manager_startup_probe`. It composes
`allocate_construct_publish` with the constructor model using synthetic storage.
The manager request is 384 bytes with alignment argument 8. A null allocation
skips construction and publishes the explicit fallback; it does not automatically
assume a zero startup register. Native allocator behavior and destruction remain
outside this reconstruction.

`python3 -m engine.examples.allocation_policy_probe` adds the recovered context
selector and allocator dispatch/retry policy to that startup composition. The
example uses synthetic heap services and demonstrates a failed first allocation,
one recovery, allocator reload and successful construction/publication.
[allocation_policy.py](allocation_policy.py) implements the verified local policy;
actual allocator objects, context identities and failure handling remain supplied.
