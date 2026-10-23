# Scheduler reconstruction and modding release gates

Scheduler reconstruction is the current primary goal. The independent runtime is the testbed; rendering and broader gameplay expansion take second priority. Progress is tracked by evidence gates rather than a coverage percentage.

## Current priority: scheduler-wide mod integration

The user's current priority is understanding the whole scheduler and enabling
mods across subsystems. Deterministic stepping is supporting instrumentation,
not the primary release milestone. Preserve the timing research, but do not make
perfect replay a prerequisite for unrelated scheduler or subsystem work.

The next milestone is a **qualified engine-phase command contract**: identify
where a bounded command can execute, what work it is ordered before/after, which
objects it may access, how completion is reported, and how unloading cancels or
drains it. The current host plugin thread is not an engine phase. Existing
held-world player setters do not establish arbitrary mutation safety.

| Workstream | Existing evidence / runnable implementation | Next proof needed |
| --- | --- | --- |
| Registration and dispatch | Mixed scheduler, recovered frame graph, BeginEngineFrame binding | Qualified native callback context and per-request association |
| Command publication | Hierarchy command producer/flush research; begin_commands_probe | Producer publication ordering, full-queue handling, and direct executor callers |
| Completion and exclusion | Ordinary dispatch finalization; explicit graphics sibling probe | Operation-specific exclusion from graphics, loading, idle tasks and alternate release |
| Ownership and lifetime | Player identity events, link checks, animation retirement research | Stable generation and invalidation contracts across queued command execution |
| Subsystem interfaces | Native player velocity/pose API; animation and asset research | Independently qualify each animation, terrain, environment or entity operation |

Immediate sequence:

1. Audit command producer publication and all executor entry paths; retain
   queue-full and pending-count mismatches as explicit cases.
2. Qualify an engine-phase receiver and observe commands there without mutation.
   Capture request identity, thread context, entry/exit and owner generation.
3. Integrate one already-understood operation through that context with bounded
   admission, stale-generation rejection, receipts and unload/drain rules.
4. Extend capabilities only when their subsystem lifetime and ordering contracts
   are established. Do not expose arbitrary addresses as a substitute for this work.

A whole-process idle claim is not required for every mod. Each operation must
establish exclusion from the specific readers/writers it can conflict with.
The idle-task producer and loading-thread contracts remain independent research
tracks because ordinary frame completion does not cover them.

## Current evidence

| Area | Established | Remaining boundary |
| --- | --- | --- |
| Frame timing | Constructor defaults, smoothing ring, float32 mean, frequency table, accumulator cap and subdivision arithmetic | Matched original execution oracle across policies |
| Job dispatch | Queue/helper accounting; three-category local/shared traversal, affinity tests and job-specific occupancy selection | Concrete per-job assignments, configuration upper bound, other subclasses and native thread context |
| Completion | Claimed receiver count is separate from running callbacks; ordinary finalization requires returned workers | Exceptional paths and whole-engine quiescence |
| Frame rearm | Action completion feeds downstream dependencies into EndFrame, which prepares and resubmits the root | Mode-specific paths, external callers and safe native control |
| Root routing | Root-to-Step edges, global mode read, two owner-mode reads and rebuild gate | Caller serialization and live mode values |
| Mode writes | Named stages copy global flags; guarded clear preserves the ordinary owner predicate value | Exhaustive writers and cross-thread visibility |
| Provider chains | Both AI provider entry-to-terminal graphs and concrete owner/getters | Callback workloads, receiver populations and later perception rewiring |
| Event control | Request byte, end-frame branch, restart operation, exact handle consumer and outer caller order | Protected platform targets/status, outer interface implementation and owner destruction |
| Input | Repopulation callbacks, PreAI category registration, composed claim/worker/completion/release tests, reset adapter and portable differential fixtures | Active configured alternatives, actual device-sample age and player substep correlation |
| Membership | Indexed insertion/deduplication; prior live player observation in BeforeSimulation registry 25, with registry 24 empty in that capture | Identity across later sessions, gated inner ingestion and request-correlated sample freshness |

The EndFrame result is a specific storage-ordering proof for the inspected ordinary action route. The next root may be submitted while EndFrame itself still has positive execution/outstanding accounting. It is not a universal idle point or permission to replace arbitrary engine state.

The [current input-route boundary](../docs/reconstruction/INPUT_TO_ACTION_ROUTE.md#current-reconstruction-boundary) distinguishes completed category joins from the remaining live and concurrency checks. Controlled CPU-context interleavings exercise callback overlap and failed claim CAS; they do not establish native thread safety.

## Evidence guide

- Timing: [smoothing](../docs/reconstruction/SCHEDULER_SMOOTHING_AUDIT.md), [constructor and lifetime](../docs/reconstruction/SCHEDULER_LIFETIME_AUDIT.md).
- Dispatch and release: [rearm rules](../docs/reconstruction/SCHEDULER_REARM.md), [wait helper](../docs/reconstruction/WAIT_HELPER_DISPATCH.md), [alternate release](../docs/reconstruction/ALTERNATE_DEPENDENCY_RELEASE.md), [backend worker registration](../docs/reconstruction/BACKEND_WORKER_REGISTRATION.md).
- Frame graph: [action caller](../docs/reconstruction/ACTION_REARM_CALLER.md), [EndFrame handshake](../docs/reconstruction/ENGINE_LOOP_HANDSHAKE.md), [root route](../docs/reconstruction/ENGINE_ROOT_STEP_ROUTE.md), [mode writers](../docs/reconstruction/ENGINE_MODE_WRITERS.md), [provider chains](../docs/reconstruction/ENGINE_PROVIDER_CHAINS.md).
- Control event: [submission branch](../docs/reconstruction/ENGINE_EVENT_SUBMISSION.md), [consumer and request](../docs/reconstruction/ENGINE_EVENT_CONSUMER.md).
- Player path: [input placement](../docs/reconstruction/SCHEDULER_INPUT_AUDIT.md), [action callbacks](../docs/reconstruction/ACTION_RESET_CALLBACK.md), [processor](../docs/reconstruction/ACTION_PROCESSOR.md), [membership](../docs/reconstruction/SCHEDULER_MEMBERSHIP_FOLLOWUP.md), [batch epochs](../docs/reconstruction/SCHEDULER_BATCH_EPOCH.md).
- Teardown: [submission/lifetime](../docs/reconstruction/SCHEDULER_SUBMISSION_FOLLOWUP.md), [optional children](../docs/reconstruction/SCHEDULER_CHILD_LIFETIME.md), [child type boundary](../docs/reconstruction/PHYSICS_WORLD_CHILD_TYPES.md).

## Executable reconstruction

The [mixed scheduler](../docs/reconstruction/MIXED_SCHEDULER_IMPLEMENTATION.md) combines selected range, one-shot callback, terminal and conditional semantics, with immediate normal/alternate dependency effects and explicit dispatch accounting. It complements the smaller [request/credit](../docs/reconstruction/REQUEST_STATE_MODEL.md) and [alternate propagation](../docs/reconstruction/ALTERNATE_DEPENDENCY_MODEL.md) references. Default queue ordering, handler version labels and adapter fault policies are explicit implementation choices. An optional recovered queue policy now implements category traversal, eligibility and signed occupancy scoring with explicit caller-supplied assignments.

```sh
python3 -m engine.examples.mixed_scheduler_probe
```

The synthetic probe runs three cycles, bypassing motion on the second. It records the next root as scheduled while the EndFrame-like callback still has one execution and one outstanding dispatch. This is executable consistency with recovered local rules, not an original-game trace. The [gameplay integration](../docs/reconstruction/GAMEPLAY_JOB_INTEGRATION.md) now offers optional mixed dispatch of actual phase work. Its five-phase graph and fresh instance per substep are explicit owned policies.

The existing `JobExecutor` remains a designed dependency executor with retained callback identity, quiescent replacement and version-qualified restore. Its states are not native job states. `SchedulerController` owns serialized submissions, pause tokens, fixed-tick or planned-frame stepping and rollback for our runtime. Its guarantees require exclusive ownership and do not establish native pause safety.

## Runtime timing experiment

```sh
python3 -m engine.experiments engine/examples/scheduler_probe.json --output /tmp/scheduler-report.json
```

The recorded synthetic experiment ran 171 frames and 280 substeps, retained all 1,636 trace records and matched replay state hashes. Its 80 ms stall remains raw in smoothing history while consumed accumulation is capped near 66.67 ms. A separate 6,000-frame timing stress check covered all policy branches and midpoint continuation. These are independent-model checks.

`GET /trace` exposes the local inspector's serial trace. A planned frame is not an execution receipt. A failed outer frame invalidates its earlier local substep commits; attempted trace events remain for diagnosis. Trace overflow reports dropped events, and restoring a checkpoint restores that trace branch. No cross-thread native causality follows from the serial sequence numbers.

The owned pause controller's separate 200-frame check completed 300 substeps with replay agreement, stale-token rejection and no drops. See [validation scope](VALIDATION.md) for current tests and limitations.

## Next implementation and release gates

The [scheduler observation adapter](../docs/reconstruction/SCHEDULER_OBSERVATION.md) now supplies exact-size decoding and two guard-bracketed sweeps for the recovered animation job topology. Its transport and selected-player ownership join remain external. It provides no native pause operation and cannot establish atomicity from repeated reads.

1. **Owned inspection and mutation contracts.** Optional mixed gameplay dispatch now passes parity, replay and rollback tests. Expose useful phase inspection and bounded owned mutations without inventing native topology or persistent graph ownership.
2. **Native event contract.** Resolve protected handle operations, the outer interface callback and owner destruction. The request byte and wait-shaped helper are concrete leads, not sufficient pause guarantees.
3. **Active membership and input freshness.** Join the selected player to its motion batch, eligible world, scheduler instance and submitted request. Match action production to consumption; equal vector values or wall-clock input delivery are insufficient. *Membership observed:* the selected actor is in registry entry 25 / `Physic::BeforeSimulation` (not entry 24, which was empty), whose slot-`0x270` dispatch is the traced ingestion route. An entry probe recorded it once per `BeforeSimulation` request within each Step frame, and an entry/exit probe measured its call completing before `PhysicsWorldStep` of the same request in 701 of 701 requests ([observation](../docs/reconstruction/MOTION_MEMBERSHIP_OBSERVATION.md#order-against-physicsworldstep)). Actor gates, riding state and freshness remain open.
4. **Original execution oracle.** At a justified observation boundary, record matched entry/exit events, job identities, branch reads and drop accounting. Keep independent thread timelines separate until causality is proved.
5. **Native pause/single-step.** Require exclusion of new submissions, completion of relevant claimed work, valid owner lifetime and required thread/TLS context. Validate repeated pause/step/resume and world changes before publishing process-control support.
6. **Modding release.** Publish stable owned handles, phase-specific mutation contracts, callback version identity, failure containment and reproducible mod state. A working independent engine API does not imply safe modification of the original process.

Full scheduler and engine reconstruction remain incomplete. Green reference tests, static endpoint graphs and local drain observations each support their own scope; none substitutes for these remaining release gates.

The [outer-interface candidate](../docs/reconstruction/ENGINE_OUTER_INTERFACE.md) reaches the stop-request writer but lacks a proved caller argument binding. The [owner-destruction audit](../docs/reconstruction/ENGINE_OWNER_DESTRUCTION.md) retains the exact missing teardown and event-close joins. These narrower leads supersede any assumption that the consumer alone supplies an owner-lifetime guarantee.

The [queue-selection audit](../docs/reconstruction/SCHEDULER_QUEUE_ELIGIBILITY.md) now provides exact traversal, affinity, integer score and tie rules. The [executable queue policy](../docs/reconstruction/QUEUE_POLICY_MODEL.md) implements those rules as an optional mixed-scheduler policy. [Queue producers](../docs/reconstruction/SCHEDULER_QUEUE_PRODUCERS.md) identify worker-count initialization and required-mask routing. Concrete job assignments and configuration bounds remain open. The [trace analyzer](../docs/reconstruction/TRACE_ANALYSIS.md) now separates retained phase evidence, aborted attempts and incomplete recordings through a read-only testbench endpoint.

The [motion job destructor audit](../docs/reconstruction/MOTION_JOB_DESTRUCTION.md) establishes that range storage cleanup precedes a conditional base-job wait. Its outer lifetime contract and wait-flag writers remain open. The local destructor must not be exposed as a native drain operation.

Optional explicit worker topology now connects recovered routing to selection and dispatch identity. The [queue policy guide](../docs/reconstruction/QUEUE_POLICY_MODEL.md) describes controlled interleavings and the runnable 100-receiver probe. Native thread/TLS behavior and dynamic worker lifetime remain outside this model.

The [worker context audit](../docs/reconstruction/WORKER_THREAD_CONTEXT.md#idle-and-notification-counter-protocol)
now connects idle decrement, coalesced notification and wait-region accounting.
Pure counter helpers cover both operation orderings; protected event reset and
signal-retention semantics remain unresolved. Waiting-count observations do not
establish a native pause boundary.

A separate [idle task worker pool](../docs/reconstruction/IDLE_TASK_WORKERS.md)
executes and disposes of queued virtual tasks outside the ordinary range-job loop.
Its submission, stop and lifetime joins remain open and must be considered before
claiming whole-engine quiescence.

The [loading-thread lifecycle](../docs/reconstruction/LOADING_THREAD_LIFECYCLE.md)
provides a separate drain/stop/wake/join sequence. Its two drain fields concern
resource destruction; submission exclusion and other loading phases remain open.

Owned tuning and rig/clip replacement now use the controller's pause-token gate,
transactional validation and fresh generations. Replay and stale-token tests cover
these mutations. The separate controller HTTP service now exposes this contract to local scripts.
Native loading integration remains separate work.

[Recovered clock holds](../docs/reconstruction/CLOCK_TREE.md) affect elapsed time rather than job quiescence. Serial tree behavior is instruction-validated, including child propagation while held. They must not replace the native submission-exclusion and returned-worker release gates.

The [EndFrame adapter target lookup](../docs/reconstruction/ENGINE_EVENT_ADAPTER.md) is now instruction-emulated with synthetic targets. Its runtime slot value and target module/export are the next concrete read-only check. Reset/wait adapters and whole-frame drain coverage remain separate gates.

The [live EndFrame target lookup](../docs/reconstruction/ENGINE_EVENT_ADAPTER.md#live-target-resolution) now resolves exactly to `kernel32.dll!SetEvent`, with 75 matching live adapter spans. Signal API identity is established for that Wine session; signal execution/status, reset/wait identity, lifetime and complete drain coverage remain open.

The [reset and wait adapters](../docs/reconstruction/ENGINE_EVENT_ADAPTER.md#live-handshake-resolution) now resolve to `ResetEvent` and `WaitForSingleObject` (infinite timeout) in a fresh session that also reproduced `SetEvent`. The handshake's API identities are closed; creation target/failure, close/lifetime, observed return status and drain coverage remain the open event gates.

Event [creation](../docs/reconstruction/ENGINE_EVENT_ADAPTER.md#creation-close-candidate-and-live-owner-state) resolves to `CreateEventA` with no failure branch. The close candidate is `CloseHandle`, but the engine-holder close and the owner's constructor caller are reached only through protected code. The remaining event gates are owner lifetime, observed call status and EndFrame drain coverage.

[Frame graph coverage](../docs/reconstruction/ENGINE_FRAME_GRAPH_COVERAGE.md): every statically reachable engine job precedes the `EndFrame` signal; off-graph workers, loading, async services and `EndFrame` itself remain outside it. The engine's stop-mode bypass (`UpdateWhileEngineIsPaused`) is a native whole-world step suppression, but it is not the in-game menu. Finding its real entry/exit is the next concrete step toward a native pause.

Stop mode has concrete entry points: confirmed window close, a world-processing flow, and a Backspace case in a keyboard command dispatcher that live input did not reach. It is a candidate native world-suspension boundary; using it for modding still requires a safe trigger, an observed bypass while it is held, and proof that resuming restores ordinary routing.

**Native suspension demonstrated.** [Entering stop mode live](../docs/reconstruction/NATIVE_STOP_MODE.md) suspended world `Step` for 165 frames while the frame loop, rendering and `UpdateWhileEngineIsPaused` continued, and clearing it resumed `Step`. This advances gate 5 (native pause/single-step) from static routing to an observed boundary. Single-step timing, the native side effects and repeated-toggle stability remain before a modding release.

**Native single-step demonstrated.** [35 of 35 released requests](../docs/reconstruction/NATIVE_STOP_MODE.md#single-step) executed exactly one world `Step` from held stop mode. Gate 5 now has an observed pause/step mechanism; its remaining items are native side effects, per-step time/substep/input accounting and an in-process trigger.
