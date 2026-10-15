# Reconstruction progress and next work

Status: active implementation. Scheduler reconstruction is now the main priority; see [release gates and experiments](SCHEDULER_ROADMAP.md). The requested full reconstruction is not complete. This file is the continuation point across implementation passes; do not restart or replace the existing prototypes casually.

Latest: Snow mod host 0.5 adds player placement through the engine's own routine (`set_player_pose` for plugins, `player.set_position` for clients; held only, at most 100 units per move). Live while riding: a 3-unit lift with velocity kept read back exactly and the player carried on from there; the same lift with zero velocity was undone in the first step, cause not yet known ([details](../native/snow_host/README.md#player-state-host-03)). Fixture 52/52.

Previous step: Snow mod host 0.4 finds the player in-process (engine root records to world to motion receivers; live: same player as the external acquisition) and adds velocity assignment through the engine's own routine. The player is two coupled bodies; assigning only the main body was undone by the heavier rider body within a few steps, while assigning both (the routine's own flag) took effect live: set to zero the player nearly stopped, and set to 12 units/s upward it rose about 0.12 units per step for ten steps ([details](../native/snow_host/README.md#player-state-host-03)). Fixture 47/47. Next: position assignment.

Previous step: the [Snow mod host 0.3](../native/snow_host/README.md#player-state-host-03) gives plugins and clients their first game state: the selected player's body (position, orientation, linear and angular velocity), bound from a validated external acquisition and re-checked on every read. Plugins may read it only while the simulation is held. A Wine fixture passed 42/42 checks. In one bounded live session paused mid-ride, the player stayed still while held and moved after each of 10 single steps (all exactly one), by speed × 8.8–11.0 ms, about one world request. The example plugin read it on every step and was refused after resume. Next: in-process player acquisition, then guarded setters.

Previous step: gate 3 [order against `PhysicsWorldStep`](../docs/reconstruction/MOTION_MEMBERSHIP_OBSERVATION.md#order-against-physicsworldstep). A static chain from the world reaches the physics state whose `PhysicsWorldStep` job the setup registers as `BeforeSimulation`'s successor; the live chain matched every check. An approved two-pointer probe (call wrapper on `BeforeSimulation`, entry pass-through on `PhysicsWorldStep`, both restored) recorded 701 requests: the actor's call entered and returned once per request, and every receiver call returned before the world step of the same request began (701 of 701, median gap 11 µs). Next: actor gates, riding, input freshness.

Previous step: gate 3 [motion membership](../docs/reconstruction/MOTION_MEMBERSHIP_OBSERVATION.md). Static joins identify three action-graph jobs that call receiver slot `0x270` through one thunk: `PreBeforeSimulation` (registry entry 24), `Ai::UpdateAIPreUpdate` (entry 5) and `BeforeSimulation` (entry 25). In a guarded passive live session, entry 24 was empty and never allocated, while the acquired player actor was receiver 2 of 5 in entry 25 and at the same index in `BeforeSimulation`'s gathered storage. Its slot `0x270` is the traced player update reaching action ingestion. Registries hold components, not entities: the entity owns receivers in 12 of 32 entries. A new passive reader and registry scan have 13 synthetic tests; the full suite passes. A passive burst showed both batches submitted together about every 12 ms. An approved entry probe then swapped one callback pointer for 10 s and restored it. It found the actor entered exactly once per `BeforeSimulation` request (1,009 of 1,009), inside each world Step frame, on 10 worker threads. Order against `PhysicsWorldStep`, actor gates, riding state and input freshness remain open.

Previous step: the [Snow mod host](../native/snow_host/README.md) moved native pause, single-step and resume in-process behind a loopback JSON command channel, with a serial executor, a recovery lease and a private build-specific adapter. In one bounded live session, 10 of 10 steps released exactly one world `Step`. Resume used the engine's clear routine without the fallback restore, and Step advanced for 20 s afterwards. A Wine fixture with a synthetic adapter passed 20/20 protocol and recovery checks. Next: repeat under movement and longer step runs, measure what a released step simulates, then add an engine-ordered execution point and the versioned plugin API.

Previous step: the [engine's own setter and clear routine](../docs/reconstruction/NATIVE_STOP_MODE.md#entering-and-leaving-through-the-engines-own-routines) entered and left stop mode live. Both produce a one-frame cut to a pause camera and back, the likely source of the per-step flash. Earlier: stop mode suspends the [whole simulation half of the frame](../docs/reconstruction/NATIVE_STOP_MODE.md#what-stop-mode-suspends), including camera, input and sound jobs. Static analysis and emulation indicate a [released step simulates about one frame](../docs/reconstruction/NATIVE_STOP_MODE.md#what-a-released-step-simulates) in 1–2 substeps, while the world millisecond timestamp jumps by the hold length. The frame-graph proof for four per-frame jobs is corrected to unproved. Next: the native notification and clear protocol (a per-world pause/resume pair was located) and a live timing check.

Previous step: [native single-step](../docs/reconstruction/NATIVE_STOP_MODE.md#single-step). 35 of 35 releases from held stop mode ran exactly one world `Step`, re-armed within 12 ms, while rendering and the paused job continued. Pause and single-step at engine-request granularity now work live. Next: native transition side effects, elapsed-time/substep accounting per released request, and an in-process toggle.

Previous step: [native stop mode](../docs/reconstruction/NATIVE_STOP_MODE.md) was entered and cleared in the live game with a guarded four-byte write. `Step` stopped executing, `UpdateWhileEngineIsPaused` ran every frame and rendering continued; clearing restored ordinary routing within one request. This is the first original-process write and the first demonstrated native world suspension. The native setter notification and clear-side transitions were not reproduced. Next: a between-frame single-step toggle and accounting for those side effects.

Previous stop-mode result: [recovered callers](../docs/reconstruction/ENGINE_MODE_WRITERS.md#recovered-stop-mode-callers) show the engine enters stop mode on confirmed window close (`WM_CLOSE` with `wParam == 0xC0FFEE`) and in a world-processing flow. A Backspace toggle exists in a keyboard command dispatcher, but live Backspace input did not change the mode. Next: tie the world-flow caller to loading/world transitions, then observe one natural entry/exit together with the event and Step bypass.

Previous step: the [engine frame graph](../docs/reconstruction/ENGINE_FRAME_GRAPH_COVERAGE.md) is recovered from setup, preparation and Step wiring. All 30 statically reachable engine jobs precede `EndFrame`, and the mode bypass is named `Engine::EngineLoop::UpdateWhileEngineIsPaused`. So the `SetEvent` in `EndFrame` follows the whole engine-owned frame graph, though not off-graph workers, loading or `EndFrame` itself. A live check showed the in-game menu does not enter that stop mode; the mode had been entered earlier in the session. Next: find which caller enters stop mode (startup/loading candidates) and observe one natural entry/exit with the event state. No native scheduler mutation.

Previous step: the [engine event lifecycle](../docs/reconstruction/ENGINE_EVENT_ADAPTER.md#creation-close-candidate-and-live-owner-state) is resolved to `CreateEventA` (manual-reset, unsignaled, result stored unchecked), with the close candidate confirmed as `CloseHandle` but still not bound to the engine holder. A second fresh passive session reproduced the handshake targets and sampled the engine during gameplay: stable owner and handle, start=1, alternate mode=0. That is consistent with the consumer parked in its infinite wait. Next: engine close/owner lifetime (protected caller) and EndFrame drain coverage. No native scheduler mutation.

Previous step: the [engine event handshake](../docs/reconstruction/ENGINE_EVENT_ADAPTER.md#live-handshake-resolution) is resolved to exact `kernel32.dll` exports: restart `ResetEvent`, alternate EndFrame `SetEvent`, consumer `WaitForSingleObject` with an infinite timeout. The reset and wait adapters were instruction-emulated (40 synthetic states each) and then joined to one fresh passive live capture by 47 and 48 matching spans; the EndFrame result reproduced. No target was invoked and no return status or wait completion was observed. Game closed deliberately; configuration restored. Next: event creation target and failure path, handle close/owner lifetime, and which outstanding work the signaling EndFrame covers. No native scheduler mutation.

Previous step: [two passive event-target observations](../docs/reconstruction/ENGINE_EVENT_ADAPTER.md#live-target-resolution) resolved the EndFrame adapter to the exact `kernel32.dll!SetEvent` export.

Latest scheduler event lead: [the protected EndFrame adapter](../docs/reconstruction/ENGINE_EVENT_ADAPTER.md) now has a concrete target-decoding formula and tail-transfer contract, validated with 40 synthetic states. The analysis image's stored target decodes to a noncanonical address; this failure is preserved rather than guessed away. Next passively read the one encoded slot in the running game and resolve its actual module/export, then apply the same method to reset/wait. No original event API or safe stop boundary is claimed yet.

Latest clock control reconstruction: [deferred holds and full serial tree updates](../docs/reconstruction/CLOCK_TREE.md) matched 160 original three-node update cases plus ten native pending-request boundary cases. Holds zero elapsed time but do not suppress child traversal or invocation accounting; a previous-source child can advance from its parent's prior interval. The immutable adapter preserves these behaviors and exposes no native scheduler mutation. Concurrent request consumption and native locks remain unproved. All 639 repository tests pass.

Latest passive clock result: [ten guarded live samples](../docs/reconstruction/CLOCK_OBSERVATION.md#original-game-baseline) across two fresh player acquisitions established current root membership for all three world clocks. Mode 2 and a one-second cap were stable; ordinary intervals were 11.28–17.28 ms, with matching root/world bits, no holds and unit scales. No debugger or riding input was used. A debugger pause hitting that cap is now a supported hypothesis for the earlier `1.0`, not a proved cause. The research game was deliberately closed and settings restored. Next correlate component selection/packet state with the clocks and recover request/input ordering; safe scheduler stepping remains open.

Latest clock hierarchy preparation: the [constructor-to-root connection](../docs/reconstruction/CLOCK_OBSERVATION.md) now establishes unique registration of the three world clocks. A bounded passive reader returns driver mode, root/world intervals, holds/scales and membership indices, with before/after link checks. Five synthetic tests pass and the full suite passes 634 tests; no live clock capture has run yet. The private fresh-acquisition runner can collect these observations without LLDB. Next run that bounded passive capture, then decide whether another debugger comparison is needed.

Latest clock-driver reconstruction: [frame-clock policies](../docs/reconstruction/FRAME_CLOCK_POLICY.md) now expose fixed, table-based, capped, history and fallback modes. The exact policy block matched 480 synthetic instruction-emulation cases, including a history index boundary that writes a neighboring native field. That behavior is reported explicitly; no live occurrence or gameplay bug is claimed. All 629 repository tests pass. Next acquire the active driver mode and clock hierarchy passively before interpreting the animation packet's `1.0`.

Latest live animation observation: [one guarded interface-call pair](../docs/reconstruction/ANIMATION_CALL_TRACE.md#original-game-observation) captured the selected player, with clean breakpoint removal and detach. Interval `1.0` and status bytes `[0, 0, 1]` were unchanged. This proves the narrow call ran, not full pose evaluation or safe stepping. [World-clock producer arithmetic](../docs/reconstruction/WORLD_CLOCK.md) now has an explicit adapter and 320 exact native comparisons. The full suite passes 625 tests. Next trace per-frame clock inputs and compare idle/movement without interpreting debugger elapsed time as gameplay cadence.

Latest packet instrumentation: [selected-component filtering and packet collection](../docs/reconstruction/ANIMATION_CALL_TRACE.md) passed an isolated Wine/LLDB fixture with alternating component identities. Three selected before/after pairs retained the exact float32 interval and status changes; unrelated calls were filtered. The public analyzer preserves unmatched calls and rejects pairing across reported gaps/errors. Seven added tests bring the suite to 620 passing tests. Next build a fresh original-game configuration and attempt the narrow call-site capture; no live game attachment occurred during this packet pass.

Latest debugger preflight: a [bounded asynchronous LLDB observer](../docs/reconstruction/ANIMATION_DEBUGGER_BOUNDARY.md) passed isolated Wine fixture tests for three entry/return pairs, a no-event deadline and signature-rejection cleanup. Hardware breakpoints were removed and all fixtures detached/exited normally. Six static spans establish the animation-interface before/after call sites and stack-packet recipe. Next implement and fixture-test selected-component filtering and packet collection before a live attempt. No original game was accessed during this preflight; no scheduler step control was added.

Latest live join: the [membership reader](../docs/reconstruction/ANIMATION_MEMBERSHIP_OBSERVATION.md) found the selected player's Kino component at index 3 in a four-receiver source list and at the same index in four-slot gathered storage. Remaining claims were zero. The source, stored-pointer and execution claims remain separate; no callback execution was observed. Six new reader tests bring the suite to 613 passing tests. Next: matched component entry/exit, packet clock and thread/request identity. The successful session was stopped and settings restored.

Begin-path follow-up: [90 isolated instruction cases](../docs/reconstruction/SCHEDULER_BEGIN_PATHS.md) distinguish immediate empty-range completion from callback queuing for the live-matched tables. A runnable partial-graph example shows zero between-job execution samples despite three accounted callbacks. Next: verify the player's animation population and capture one callback interval; the empty-range shortcut cannot explain the three callbacks on their ordinary path.

Live follow-up: [three fresh acquisitions succeeded](../docs/reconstruction/NATIVE_SCHEDULER_OBSERVATION.md) in one bounded Highball session. The selected world's graph and all seven job tables matched; 44 ordinary sweeps and 283 complete burst groups showed advancing request counts and changing holds. All sampled execution counters were zero, so no worker interval or safe pause point was established. Next investigate animation receiver membership and immediate/ordinary dispatch paths before interpreting further zero samples. The session ended at its time limit, restored configuration and left no game/Wine processes running.

Latest observation work: a [guarded scheduler collector](../docs/reconstruction/SCHEDULER_OBSERVATION.md) decodes seven animation/action job headers and the animation claim count through a caller-supplied read transport. Nine synthetic tests check its failure and reporting contracts. The action graph is now resolved through world+`0x1038`, with a graph-to-world backlink guard, separately from the earlier physics scheduling state. A private command connects fresh player/world acquisition to this collector; the live follow-up above validates this path for one session. The constructor verifier passed 32 instruction slices and five table bindings, and four world/graph instruction spans were checked against the hash-matched image. Next: resolve the receiver-membership and dispatch questions identified by the live capture. Equal counters never establish safe stepping.

## Implemented and integrated

- Standard-library source tree with explicit Z-up/XYZW conventions and synthetic scenarios.
- Snowboard, ski, walking, wingsuit and paraglider update paths.
- Shared input snapshots, tick stepping, recovered unsmoothed schedule option and state publication.
- Complete owned-state checkpoint/restore and command replay including frame scheduling and paused state.
- Synthetic rig/clip runtime, crossfade/additive animation, hierarchy and palette helpers.
- Environment clock/weather, camera spring/follow state and event-driven scoring.
- Terrain/material queries, swept obstacle collision, fault rollback and incident history.
- Rig/pose/trace inspection, contact-cell and IK probe functions and local browser/HTTP inspector.

These modules mix recovered local arithmetic and documented substitutes. Read README and module evidence before assigning fidelity.

## Passes completed in this implementation run

1. Independent modules and a headless integrated simulation.
2. Replay/transaction hardening, checkpoint continuation and camera state.
3. Browser inspection and numerical slope-contact regression fix; standalone contact/IK probes.
4. Optional six-cell rigid hull with rotating inertia and conserved world angular momentum; recovered 60 Hz sampling, inclusive wrapping and lazy graph readiness kernels.

5. Serializable pose graphs, ordered blending/masks/selectors, checkpointed graph clocks and transactional resource/tuning APIs.
6. Read-only archive framing/codec adapter and typed private rig/clip importer with independent translation/rotation tracks. Private corpus checks completed; payloads remain outside this repository.

7. Recovered smoothing/ring/table policy, constructor and conditional ingestion-job ordering audits, bounded runtime phase traces and headless scheduler experiments.
8. Action-binding reset writer and owner teardown follow-ups; owned pause/step controller with exclusive submissions and stale-token rejection. Native exclusion remains unproved.
9. Preserved standalone rig assembly, root-motion extraction, procedural pose stages, motion-state observer and provider-boundary modules. These are not yet wired into the default gameplay selector.

10. Further action callback/map closure, range-consumption arithmetic, optional child lifecycle tracing and queued backend completion. New local action/range kernels have synthetic boundary tests; no native execution claimed.

11. Default action processor and explicit composed action pipeline; backend worker callback-registration chain; ordinary child-deserializer exclusion. Native active selection and owner exclusion remain open.

## Next implementation priorities

Scheduler work takes precedence over the broader backlog below: prove active membership/request identity, action-payload freshness, owner lifetime and submission exclusion. Implement and validate the owned dependency executor, then compare against a separately authorized original execution trace. See [scheduler roadmap](SCHEDULER_ROADMAP.md).

1. Refine the implemented rigid_cells mode with recovered face-area/contact selection, layered materials and original mass/body representation choices. The current six-cell box, volume weights and substrate are synthetic. Preserve separate pressure/contact contributions and elapsed/derivative intervals.
2. Connect a verified active rider graph to the implemented graph runtime. Graph arithmetic is available; authored graph wiring and timing remain unresolved. The default selector remains a labeled independent design.
3. Trace and implement active base/addon rig assembly and authored UID-to-compiled-key conversion. Until resolved, use explicit caller policies and report missing joints before fallback.
4. Extend the implemented local archive/pose adapter to additional validated resource types. Current checks cover every available archive index and selected compressed resources, not every payload. Do not publish extracted payloads or Studio-authored tracks.
5. Extend procedural layers with explicit IK request mappings, landing inputs and actor-to-pose timing. A callable target kernel is not a complete full-body solver.
6. Trace original action-vector writers and sample publication. Use these findings to refine compatibility scheduling; our input generation remains a designed feature.
7. Add terrain streaming, actual mesh rendering, material/lighting pipeline and local asset visualization after coordinate/binding tests. The current canvas is a diagnostic view.
8. Refine tricks, landing/crash classification, ragdoll, respawn, air zones, walking snow-depth behavior, scoring event ownership and camera arbitration using the existing research and focused new checks.
9. Add audio, persistence/version migration, packaging and performance work after the behavioral interfaces stabilize. No original networking or online service compatibility is claimed.

## Acceptance gates for every pass

Add evidence and tests for the changed behavior. Run the full suite when shared state or interfaces change. Preserve source manifests, no game payloads, no absolute machine paths, and valid links. Keep synthetic, asset-decoded, binary-derived, video-estimated and Studio-authored categories explicit. Update this file with completed work, actual test results and the next concrete task.

Validation checkpoint: see [validation scope](VALIDATION.md) for the current suite and private adapter checks. The earlier 121-test checkpoint included the gentle-curvature regression. Five synthetic 3,600-tick sport scenarios plus their replays matched hashes with zero recorded faults. Browser step control and canvas rendering were checked; an extension resource failure and missing favicon were observed, with the favicon reference then corrected. Full game parity and production rendering remain unverified.

## Current scheduler continuation

Connected world action wrappers through the eligible-world chain to the engine Step callback and preparation/root submission. Resolved unselected-route recursion separately from ordinary completion. Added a standalone request/hold/credit reference and 14 boundary tests; full suite now passes 278 tests. Corrected membership guidance to retain the already recovered indexed insertion and duplicate-pointer check.

Next: trace the outer engine-loop completion/event handshake before repeated graph preparation, including the event-related submission branch. Preparation itself supplies no worker wait. Preserve the distinct player-membership and input-freshness gates. No original game was launched or modified.

## EndFrame and branch propagation checkpoint

The ordinary rearm caller is now identified as EndFrame, downstream of the action-completion chain. Root-to-Step edges and mode predicates are documented separately. The alternate end-frame branch bypasses root submission and reuses the engine-owned event holder touched by restart. Explicit wait-helper accounting is also verified.

Added a serial alternate-dependency model with ordinary/conditional bindings, after-traversal clearing, current-hold rechecks and order-sensitive join tests. Full suite: 288 passing tests. No original game execution, attachment or control.

Next: recover mode-byte writers and exact event waiter, then resolve the two provider entry/terminal interiors. Follow with the mixed normal/alternate scheduler implementation and a native execution oracle once active identities and observation safety are established. The prior ordinary rearm gap is closed under its stated topology; native pause/single-step and full engine reconstruction remain incomplete.

## Connected scheduler checkpoint

The mixed scheduler now executes range, one-shot callback, immediate terminal and conditional jobs together. Normal successor effects run immediately, alternate effects preserve bypass order, and dispatch tokens distinguish claimed work from returned callbacks. Low-level root submission remains available inside EndFrame before its own accounting finishes. The runnable three-cycle probe verifies an active/skipped/active route sequence. Full suite: 302 passing tests; malformed token regression fixed and covered.

Static work connects both AI provider interiors, engine mode stage copies/setters, and the exact event consumer/request byte. Protected platform operations, outer interface implementation and owner destruction remain open. The roadmap is now organized by current evidence and release gates rather than accumulated pass notes.

Next implementation: integrate owned gameplay phase dispatch through the mixed scheduler while preserving timing/replay behavior and labeling the chosen phase topology. Native investigation: protected event semantics and outer interface/owner lifecycle, followed by current player/world/request identity and source freshness. Full reconstruction and native pause/step remain incomplete.

## Gameplay dispatch checkpoint

Optional scenario `execution_mode: mixed` now runs real physics, environment, scoring, animation and camera callbacks through the mixed scheduler. Direct execution remains the default. Shared numerical methods preserve state hashes and events; a fresh graph per substep avoids stale callback ownership in checkpoints and controller rollback. Job events are forwarded into the bounded Engine trace.

Full suite: 314 passing tests. The 12-frame probe ran 28 substeps with exact direct/mixed state parity, checkpoint continuation and replay, 2,288 trace records and no drops or incidents. The phase topology and per-substep graph lifetime are explicitly designed policies.

Native research retained a candidate outer interface whose method reaches the known stop writer, but its actual caller argument binding remains unproved. The engine-owner destructor and exact event-close relationship remain unresolved; an unrelated nearby teardown was excluded. Next work: make phase inspection and safe owned mutation contracts useful through the testbench, while closing native identity/lifetime edges independently. Full native scheduler control remains unproved.

## Trace analysis and queue-policy correction

Added read-only trace analysis, exposed at `/trace/analysis`, with frame/substep correlation, phase evidence, rollback propagation and explicit incomplete-record status. Full suite: 323 passing tests. Nine analyzer cases plus an HTTP immutability check cover the new behavior.

Static queue decoding corrected the older two-category description: the selector scans three categories, local then shared queues per category. Eligibility is job-specific; occupancy score uses signed integer arithmetic, and callback jobs do not apply the receiver execution-cap predicate. The mixed model still labels its simpler queue policy as designed. Next: implement and test the recovered selection policy separately before connecting it to the mixed scheduler. Native category/mask producers and safe process control remain open.

## Recovered queue selection checkpoint

Implemented optional ordinary queue selection in the mixed scheduler: three categories, local/shared ordering, supplied eligibility, affinity filtering and signed int32 occupancy arithmetic. Enqueue resolves sentinel limits before eligibility checks. Inspection copies reflect current execution counts and do not mutate scheduler state. Default gameplay dispatch retains its explicitly designed queue assignments.

Static producer work identifies the initialized worker count as the score default, rotating worker masks and lowest-required-bit enqueue routing. Configuration bounds, per-job assignments and concurrent behavior remain unresolved. Full suite: 332 passing tests. The runnable queue probe preserves an incompatible scheduled job after eligible work finishes.

Next: reconstruct the worker initialization and enqueue routing as explicit executable contracts, retaining unknown configuration and job assignments as inputs. Native event semantics, owner lifetime, active player identity and input freshness still gate original-process control.

## Executable queue producers

Added pure worker-configuration, rotating-mask and enqueue-destination functions.
They preserve unsigned clamp and signed consumer interpretation without creating
threads. Missing worker slots remain errors rather than invented null fallbacks.
Six boundary tests include routing-to-local followed by exclusion bypass. Full
suite: 338 passing tests. No original-game execution or control.

Next: establish exact base-constructor limit comparison and concrete category/mask
assignments, then connect producer-driven queue ownership to an explicit
multi-worker execution model. Native concurrency must remain separately verified.

## Base job limit closure

A fresh instruction-level check closes the base-constructor limit formula: signed minimum of a zero-extended byte argument and signed default, then uint8 conversion. Added the executable function and boundary tests, including negative defaults and byte rollover. These values are arithmetic fixtures, not observed live configuration. Full suite: 339 passing tests. Concrete constructor overrides and job assignments remain the next static targets.

## Named AI queue assignments

A fresh static pass connects seven named AI stages to category-one construction,
base byte limits and selected explicit limit-one overrides. It distinguishes a
nearby auxiliary-mode setter from queue category and decodes its conditional
excluded-mask clear. See the AI queue assignment supplement. Later writes and
live receiver identities remain open. No runtime code changed; packaging and
links were rechecked. The last full executable suite remains 339 passing tests.

## Motion queue construction follow-up

Connected motion and pre-physics named batches to category-one construction, zero initial masks and byte-limit 255. Resolved the pre-physics setup value 32 to a virtual range-parameter setter, which writes 32 and 64 separately from execution limits. Published full setter pseudocode, including signed clamp and overflow boundaries. Next is joining those range fields to their consumers and checking later overrides. Runtime code unchanged; last full suite remains 339 passing tests.

## Range producer-to-consumer closure

Checked the concrete motion range worker and joined the two setup fields to chunk size and tail threshold, reconciling the latest construction note with the earlier batch-epoch research. Added exact setter arithmetic and a synthetic 100-receiver mixed-scheduler test using the recovered 32/64 settings. The test preserves claim exhaustion versus returned-worker accounting. Full suite: 341 passing tests. Native inter-thread order remains unverified.

## Motion job teardown boundary

Decoded the concrete range destructor and base-job wait. Remaining-count clear and owned-storage cleanup precede the optional state/outstanding spin loop; the base constructor initializes its wait flag false. This narrows the needed proof to outer lifecycle callers and later flag writers. It establishes no original-game defect or native pause guarantee. Runtime unchanged; packaging and links checked; last full suite remains 341 passing tests.

## Submission-to-destruction flag join

Joined the ordinary submission usage flag to the conditional destructor wait field. Submission sets it even when already scheduled; dependency begin alone does not. Added two lifecycle regression cases and found the immediate containing-owner teardown/free edge without claiming it supplies a barrier. Full suite: 343 passing tests. The outer exclusion/lifetime contract remains unresolved.

## Action-graph ownership closure

Matched containing-owner constructor and deleting destructor through the installed table. Construction stores the allocated action graph in the exact member later destroyed and released. The deleting wrapper adds no visible stop call. Factory/virtual lifecycle caller remains open; direct-call searches are explicitly bounded. This is a storage-identity result, not a quiescence guarantee. Documentation-only pass; packaging and links verified.

## Explicit worker interleaving testbench

Connected queue-routing producers to optional worker topology in MixedScheduler.
Explicit worker-index reservation now separates local ownership from shared
selection, preserves worker identity in dispatch records and permits controlled
overlapping claims. Five tests and the 100-receiver probe validate delayed
completion, shared callback uniqueness and immutable readiness. This remains a
serial model of chosen interleavings, not native thread execution. Factory search
for the action owner found no direct pointer/call closure; indirect and protected
paths remain open. Full suite: 348 passing tests.

## Bounded interleaving exploration

Added a symbolic worker-action explorer with fresh-prefix replay, explicit node/depth cutoffs and accounting/claim invariants. The two-worker, two-receiver fixture exhausts 315 nodes and 96 completed schedules. Blocked leaves remain distinct from quiescent completion. No native concurrency, receiver-body interleaving or external callback replay is claimed. Full suite: 352 passing tests.

## Interleaving oracle and deferred-work correction

Added active-dependency hold conservation and premature-release checks. Deliberately broken release/accounting implementations are detected by fault-injection tests. Conditional selected/bypass fixtures exhaust 48 and two schedules. Corrected quiescence reporting for deferred credit work and active dependency lists. Full suite: 356 passing tests. Exploration remains bounded to symbolic ordinary-worker API boundaries.

## Portable scheduler experiments

Added a JSON-driven explorer CLI with standalone reports and distinct exit statuses for complete, bounded, violated and invalid experiments. End-to-end CLI tests cover report generation, bounded search and source-file preservation. Full suite: 358 passing tests. The native worker upper-bound writer remains unresolved after a bounded direct-store/address-taking search; image data zero is not used as a live default.

## Explicit helper execution model

Implemented bounded range-only helper dispatch and read-only helper wait status. Helping bypasses queue selection/caps while preserving execution and outstanding accounting. Three tests cover cap/affinity bypass, empty-versus-drained state and rejected lifecycle/type misuse. Full suite: 361 passing tests. Native TLS, owner protection and nested helping remain unresolved; no blocking native wait is exposed.

## Range-worker yield counter identity

Joined the worker comparison values to the global queue manager supplied to enqueue: ordinary enqueue changes one counter, front insertion increments the other. Added exact post-range yield predicate and boundary tests. This explains stopping further claims after new queue work without interpreting the counters as frames. Front-counter decrements and job flag setters remain open. Full suite: 362 passing tests.

## Front-counter lifecycle and array shifts

Joined queue-manager zero initialization, front enqueue increment and flagged removal decrement. Removal ignores pointer-search success, so balanced counts require valid membership and stable flags. Decoded insertion/removal shift arguments without claiming the runtime copy helper or allocator internals. Front count describes flagged queued work under those invariants, not all executing callbacks. Documentation-only pass; packaging and links verified; last full suite remains 362 passing tests.

## Queue-change yield integration

Connected enqueue generation, front membership and post-range yield gates to mixed execution and helper dispatch. Current claims finish before yielding; unclaimed receivers remain scheduled and successor release still waits for actual completion. Four integration tests cover resumption, front gating, callback removal timing and uint32 counter wrap. Full suite: 366 passing tests. Symbolic exploration handles yielded dispatches; native flag setters and thread behavior remain open.

## Blocked experiment diagnostics

Reports now retain blocked paths independently of ordinary leaf examples, with waiting-job state, holds, deferred credits, active outgoing lists and worker eligibility. Existing credit and affinity regressions validate the details. A bounded native flag-writer scan found offset collisions, including a stack-local candidate, but no newly verified scheduler assignment; native flag settings remain caller inputs. Full suite remains 366 tests.

## Worker TLS producer and execution mode

Joined the ordinary worker-loop context writer to explicit helper lookup. Decoded conditional context hooks and normal-return execution-mode save/restore; connected the formerly neutral job mode setter to that TLS field. Null context skips hooks but does not prove arbitrary worker-body thread safety. Mode readers, hook implementations and exception cleanup remain open. Documentation-only pass, packaging verified; last full suite 366 passing tests.

## Concrete worker hook closure

Resolved the wrapper before/after slots through the table installed by worker initialization. Before conditionally invokes an enabled global service once per worker, latching only after normal return; absent/disabled service retries later. After is a no-op. The service implementation, producer and possible latch resets remain open. Documentation-only pass, packaging checked; last full suite remains 366 passing tests.

## Worker service implementation closure

Traced the global service writer through its factory and concrete table. Enabled reads a global byte; worker operation follows jump adapters into a callback-table loop passing zero and rereading count. Combined with the worker latch, an enabled empty table still consumes the one-time hook. Registration producers, callback semantics and lifetime remain open. Documentation-only pass; packaging verified; last full suite remains 366 tests.

## Thread callback stage protocol

Decoded the separate entry wrapper using the same callback table: stage one precedes the supplied thread body, stage three follows normal return, while the scheduler hook uses stage zero. The descriptor started flag is set before initialization callbacks and cannot prove initialization completion. Registration producers and protected thread-creation semantics remain open. Documentation-only pass; packaging verified.


## Worker idle and notification protocol

Joined idle fetch-sub to the notifier CAS and recovered counter-based retry versus
wait decisions. Added pure transition helpers and ordering/overflow tests. The
wait-region accounting starts before adapter entry; it is not a parked-thread or
quiescence proof. Protected event semantics and the separate selection gate remain
open. No game process was accessed.

Validation: full independent suite passes 370 tests.


## Worker startup and exit ordering

Recovered constructor counter/flag defaults, event-creation argument mapping,
concrete startup overrides and the registration-to-shared-startup handshake.
Startup writes execution mode six before the loop. The concrete exit hook uses a
separate latch-gated indirect cleanup target, then clears the run flag after loop
return. Event API identity, cleanup producer and the preceding stop cause remain
open. Static-only pass; last full suite remains 370 tests.


## Initial worker release join

Joined the worker initializer to a direct event broadcast over the registered
worker array. It bypasses the ordinary notification counter and occurs after
per-worker startup handshakes. The initializer marker follows signal calls, with
no worker-resume acknowledgment. Distinguished the initializer-owned collection
from runtime registration storage. Bounded stop-writer searches did not close the
external stop path. Documentation-only pass; last full suite remains 370 tests.


## Separate idle task pool identity

Rejected a same-offset worker-flag candidate by joining its actual constructor and
installed table to a separate IdleThread consumer. Recovered normal task execution,
node recycling before task invocation, task destruction, optional callback gates
and stop-check placement. This exposes an additional whole-engine quiescence
boundary. Static-only pass; full suite remains last verified at 370 tests.


## Idle-task dummy-node dequeue

Decoded queue initialization and pop retry/help/head-advance branches, including
payload transfer into the retired dummy and 16-bit tag wrap. Added an executable
observation-to-decision helper without fabricating CAS success or concurrent
memory safety. Joined manager factory publication to the consumer's global.
Submission and reclamation remain unresolved.

Validation: all 375 independent tests pass.


## Idle-pool startup count and queue identity check

Joined the subsystem startup caller to the manager factory with a literal worker
count of two. Rejected a superficially matching enqueue candidate because its
counter overlaps this manager's worker-collection storage and its dequeue differs.
Added focused routine hashes and bounded-search limits. Producer remains open;
no substitute producer was introduced. Documentation-only pass; last full suite
remains 375 passing tests.


## Cooperative idle-task consumer probe

Added an instruction-boundary consumer probe over explicitly synthetic prelinked
nodes. Tests exercise overlapping head claims, delayed payload copies, stale-head
retry and tail assistance. The example demonstrates second-task return before
first-task return without duplicate claims. Producer publication, node reuse and
native reclamation remain excluded rather than assumed safe.

Validation: all 380 independent tests pass; the runnable delayed-copy probe completes in 24 steps.


## Idle-task allocator free-stack closure

Joined queue-constructor allocation to the same tagged free-head updated by the
consumer's node return. Added exact pop/return decision helpers and tests for
chain preservation, stale full-word identity, empty pointer bits and tag wrap.
The synthetic wrap experiment establishes finite identity width, not a native ABA
bug. Node lifetime and safe republishing remain unresolved.

Validation: all 384 independent tests pass.


## Base thread entry versus destruction

Decoded competing lifecycle CAS operations: entry changes one to two, destruction
changes one to three. Destruction winning prevents the virtual body from entering;
it does not cancel a body whose entry won first. Added local transition helpers
and ordering tests, preserving the separate destructor state load and wait-result
branch. Derived worker resources are released before the common wait attempt, so
outer shutdown/lifetime guarantees remain necessary.

Validation: all 388 independent tests pass.


## Explicit join wrapper contract

Recovered the separate timeout-forwarding join wrapper, including zero-state
shortcut and zero-adapter-result state clear. Added entry/result decision helpers
and tests. Found drain/stop/wake/join behavior in a different-layout caller but did
not assign it to the ordinary scheduler without type evidence. Native owner and
submission-exclusion joins remain unresolved.

Validation: all 390 independent tests pass.


## Loading-thread shutdown receiver identity

Matched the drain/stop/wake/join object's constructor and loop table to the named
LoadingThread. Its drained fields are an exchanged pending-destruction count and
batch-busy flag. Recovered ring iteration, virtual destruction and post-stop loop
ordering, retaining the pending-count/ring-population invariant. This narrows the
quiescence claim instead of treating loading counters as physics completion.
Static-only pass; last full suite remains 390 tests.


## Destruction staging and publication join

Joined the ring insertion helper to staged-count accumulation and the later
staged-to-pending transfer. The stop poll ignores staged work and the publication
interval, making outer submission exclusion a concrete requirement. Added exact
counter helpers and tests for the handoff, batch separation and signed boundaries.
Ring-growth failure behavior and nested locking remain qualified dependencies.

Validation: all 394 independent tests pass.


## Destruction ring growth contract

Decoded preserving resize copy geometry and metadata reset, plus equal-capacity
and fresh-allocation branches. Added a bounded geometry planner and wrapped FIFO,
shrink and clear tests. Empty allocation can visibly leave capacity zero before
the caller still increments staged; nonempty growth lacks a visible null check
before copy. Allocator failure guarantees remain unproved rather than replaced
with an invented recoverable fallback.

Validation: all 397 independent tests pass.


## Ordinary worker collection cleanup boundary

Joined the initializer-owned worker pointer array to static setup and a registered
cleanup callback. The complete callback only conditionally frees array storage;
it never iterates workers or joins them. This rejects that container cleanup as
the missing shutdown coordinator and preserves separate worker-allocation and
manager-registration lifetime requirements. Documentation-only pass; last full
suite remains 397 tests.


## Owned paused mutation APIs

Added controller-gated tuning and rig/clip replacement. Successful mutations
publish an isolated validated candidate and issue a fresh pause generation;
validation failures preserve the engine and token. Tests cover stale/running/
foreign tokens, unchanged body/tick, independent input copies, rollback and replay
through mixed dispatch. These are explicit owned policies, not native hot reload.

Validation: all 401 independent tests pass.


## Controller HTTP testbench

Added a separate loopback JSON service that exclusively owns SchedulerController.
Pause, fixed/planned stepping, frame submission, tuning, resource replacement,
checkpoint restore and replay are scriptable without a direct-engine bypass.
End-to-end tests cover token generations/schema, rollback, replay, resource
replacement and request boundaries. Legacy browser inspector remains separate.

Validation: all 405 independent tests pass, including controller HTTP flows.


## Repeatable HTTP brake comparison

Added a runnable approach/checkpoint/two-tuning experiment through the exclusive
controller API. Reports retain both branches before restore, with per-frame body
and input-generation samples, trace analysis and replay evidence. End-to-end tests
repeat the experiment and compare trajectories while checking that tuning actually
changes velocity. Simulation frames determine timing; network latency does not.

Validation: all 407 independent tests pass. The default 30-frame approach plus two
30-frame branches completed with exact replay agreement and complete retained
traces. Gentle/strong final synthetic speeds were approximately 3.8433 and 0.00813
in the owned engine's units. These are implementation results, not game footage
fits or native measurements.


## Optional gameplay phase-state capture

Added bounded-record entry/return capture for physics, environment, scoring,
animation and camera, keyed to substep/frame invocation and input generation.
Animation capture includes evaluated pose. Tests establish direct/mixed numerical
parity, immutable observations, missing return on failure and explicit capacity
loss. Captures remain attempted-phase evidence until frame outcome is known.

Validation: all 410 independent tests pass.


## Failure evidence outside rolled-back simulation state

Controller execution incidents now preserve a separate 64-record attempted-trace
excerpt before rollback. Generation and explicit capture/trim loss prevent stale
sequence numbers or partial records from masquerading as committed history.
Tests verify retained animation evidence, restored primary trace/state, checkpoint
persistence and rollback even when diagnostic capture fails.

Validation: all 413 independent tests pass.


## Animation provider callback installer

Static tracing identifies the callback table as an embedded owner subobject and
connects its named `AcquireAnimationResourceById` registry entry to the exact
setter of the slot called by handle initialization. The installed lookup function
and authored UID conversion remain unresolved. Published portable pseudocode,
constructor/teardown qualifications and a bounded next binding search. No game
process was accessed and runtime behavior was not changed. Last full executable
validation remains 413 tests; this pass requires documentation/package checks.


## Animation acquire binding and resource-entry ownership

Connected the named binding caller through registry dispatch to its supplied
acquire function. Decoded wrapper allocation, unchanged key forwarding and both
ordered atomic decrement/release gates. Added portable pseudocode with lookup,
name hashing, release semantics and wrapper-to-row adaptation still explicit
unknowns. Four bounded function bodies inspected; no live game access. Last
runtime suite remains 413 tests. Documentation/package checks apply to this pass.


## Shared animation entry selection

Decoded zero-key sentinel acquisition, guarded lookup/reference increment,
packed cached index, fallback key map, block free-list creation and conditional
record rebinding. Release's inner operation remains opaque. Name hashing call
arguments now match registration under an equal seed. Added executable offset,
key-range and release-gate kernels with boundary tests. No original process
access or loaded-animation claim. Next: record lookup/binder and inner release.

Validation: all 417 independent tests pass, including four new arithmetic boundary tests.


## Animation record binding and recycling

Decoded record lookup precedence, cached-index publication, mode-dependent
deferred triples, and guarded free-list recycling. Added inner release and index
writer kernels with tests for flag distinctions and truncation. Queue consumer
and ready-resource interpretation remain open. No live process accessed.

Validation: all 420 independent tests pass; packaging and links verified.


## Resource manager processing joins loading lifecycle

Connected the 0-to-1 manager mode transition to loading pending/busy waits and
the guarded processing wrapper, including its existing staged-destruction phase.
Decoded entry-index calculation and corrected record preparation's record
argument. Deferred triple consumer remains untraced; no native pause guarantee.
Documentation-only pass; last full runtime validation remains 420 tests.


## Deferred animation triple consumer

Decoded captured-count consumption, key-only stale check, bit31 marking and
dispatch through the entry's current record. Added a decision helper and tests
that preserve the absence of generation/recycled-bit checks. Traced registry
lookup and TLS-gated per-item preparation/processing; helper semantics and
producer-to-published count transfer remain open. No native process accessed.

Validation: all 423 independent tests pass.


## Resource item dispatch protocol

Decoded optional-handle prerequisite checks, first-row preparation versus all-row
processing, normal temporary cleanup and shared reentrant guard behavior.
Published pseudocode preserves dispatch-success versus result-success distinction.
Resolver/operation identities and counter publication remain open. No runtime
change or live process access; last full suite remains 423 tests.


## Resolver mode narrows active item path

Decoded handle predicate, temporary resolver construction and row assembly.
Traced zero mode from item callers to handle-creation bypass, selecting direct
row operations on this route. Guarded operations remain generic findings, not
proved active work here. Documented row mapping and traversal boundary. Runtime
unchanged; last full suite remains 423 tests.


## Direct resource descriptor dispatch

Decoded packed effective-type selection and descriptor notification receiver
adjustment/stage ordering. Direct operations remain generic dispatchers with
unexpanded specialized/fallback work. No clip or pose semantics assigned.
Documentation-only pass; last full runtime suite remains 423 tests.


## Resource triple publication closed

Located the producer-staged to consumer-published counter transfer and checked
its zero exchange operand by bounded direct-branch register flow. Added uint32
capture/publication kernels with interleaving and wrap tests, preserving the
absence of a local wake operation and the consumer's unsigned countdown.
Outer cadence, population/lifetime and native pause safety remain open.

Validation: all 426 independent tests pass.


## Publication callback ordering

Decoded exclusion-mask callback passes around resource publication, reverse record
order, optional secondary calls and live group-count reads. Direct caller creates
a stack processing context; cadence remains unproved. Documentation-only; last
full suite remains 426 tests. No original process accessed.


## Resource publication tied to loading requests

Joined the publication wrapper to loading-thread request selection and branch
conditions, including callback status values, re-read result and active-pointer
clear-before-release ordering. Cadence is request-driven on this route; no
per-frame or global-drain claim. Documentation checks apply; last full suite
remains 426 tests.


## Consumer wait scope and request staging

Decoded single-key/lane request wait, all-request-queue wait and ascending
four-lane refill with lane1 special handling. Consumer has multiple caller
families; no universal frame cadence assigned. Capacity, allocation and producer
exclusion contracts remain open. Documentation-only; last full suite 426 tests.


## Request producer and provider refill context

Joined free-ring acquisition, request initializer call, signed lane submission and
loading notification protocol. Decoded lane1 provider query/membership recheck
and normal TLS/mode restoration. Context-submission operations remain opaque.
No process access; documentation-only, last full suite remains 426 tests.


## Request reset and packed entry references

Decoded initializer lane/kind assignment, separate packed low24 reference holds,
sentinel reset, callback/context clearing and conditional free-pool return.
Packed-reference release can defer entries and process manager work after unlock.
Capacity and deeper ownership remain open. Documentation-only; last full suite
remains 426 tests.


## Deferred cleanup reference revival

Decoded after-dequeue packed-reference recheck, hook/routing order and inner
recycle attempt. Added a decision kernel with tests for revived references,
zero/nonzero mode routing and absent records. Context assignment now establishes
retain-before-swap/release-after-swap locally. No native process access.

Validation: all 429 independent tests pass.


## Animation replacement precedence and scalar side effects

Decoded primary-before-ordered-provider selection, original-handle fallback,
output writes from unavailable matching rows, and context-callback availability.
One caller conditionally publishes the scalar after a key comparison and a row
predicate; scalar units and predicate semantics remain unresolved. This narrows
the adapter contract without inventing an animation selection policy.
Documentation-only static pass; no native process access. Last full suite remains
429 tests; no new runtime behavior claimed.


## Executable animation provider lookup contract

Added a standalone provider lookup adapter with exact scalar-bit retention,
ordered primary/secondary precedence, original-handle fallback and callback
pointer reread. Five synthetic tests exercise failure side effects and identity.
The adapter is not wired into the synthetic pose player while selection and
resource ownership remain unresolved.

Further static inspection connects the aggregate through context ownership,
identifies shared callback-table key/predicate slots, and decodes activation's
scalar write and replacement-dependent settings-byte inequality. Settings meaning,
callback targets and activation reset cadence remain open.

Validation: all 434 independent tests pass; packaging, hashes and links pass.


## Tagged animation endpoints and binding order

Recovered unsigned16 / 120 float32 endpoint conversion, first tag match,
zero-on-miss, limit cap and start/end fallback. Added a standalone synthetic
endpoint kernel with floating-point boundary tests. Decoded old-token release,
new-owner publication and bind-result storage, plus preliminary binding with zero
tags. Callback semantics, endpoint units and context identifier remain open.

Validation: 437 tests pass; packaging, hashes and local links pass.


## Named evaluator interfaces and error-resource fallback

Connected six callback names through registration, setters and concrete targets.
The unknown key/predicate are GetAnimationId and IsPlayingErrorAnimation; the
resource scalar is GetAnimationResourceLength. Decoded mutating error-entry
fallback, evaluator pool acquisition/release order and two settings-to-flag bit
assignments. Length units, bit meanings, pool lifetime and activation cadence
remain open. Static documentation pass; last full suite remains 437 tests.


## Effective animation range and inverse tick conversion

Decoded range enable/store, effective endpoint repairs, float32 x120+0.5 tick
conversion, low16 storage and optional cache reset. Added a finite-input standalone
range kernel with tests for branch precedence, equal/invalid ranges and tick
wrapping. Resource assignment uses the known packed-reference release path.
Context backoff, progress clock semantics and units remain explicit unknowns.

Validation: 440 tests pass; packaging, source hashes and local links pass.


## Playback position setters and timestamp cursor boundaries

Decoded fraction/offset setters, history/cache gates, reset's strict-before cursor
and forward traversal's inclusive boundary. Added standalone synthetic cursor
model with duplicate timestamp, exhaustion and rewind tests. Dispatch can be
skipped while cursors advance. Automatic clock update, payload delivery and the
two native count fields remain unresolved; no event system integration claimed.

Validation: 443 tests pass; packaging, source hashes and local links pass.


## Timestamp payload dispatch gates

Decoded cursor-before-filter behavior, independent boundary bits, exact mode-one
flag gate, absent-metadata bypass and payload/recipient checks. Added an isolated
gate helper and tests. Classification only marks an output byte; preparation and
dispatch follow regardless of classification result. Payload semantics and the
raw-timestamp right shift remain open. No event delivery wired into the runtime.

Validation: 446 tests pass; packaging, source hashes and local links pass.


## Animation timestamp batch ownership

Resolved the former dispatch helper as a three-array enqueue: raw payload pointer,
retained recipient entry and retained owner entry. Documented sequential append,
reference transfer and capacity invariants. Metadata lookup is a descriptor
interval type check returning the original object. Actual batch consumption and
payload effects remain open. Documentation-only; last full suite remains446.


## Timestamp batch destruction contract

Decoded reverse-array teardown, independent element/storage ownership bits, and
captured-range shared-entry release. A constructor/destructor pair supplies a
compatible owner layout, but producer context identity and normal delivery remain
unproved. No idempotent drain or payload destruction is inferred. Documentation
pass; last full suite remains 446 tests.


## Static animation batch owner join

Connected owner+batch through setup descriptor, evaluator storage and timestamp
consumer to enqueue. Decoded cursor allocation/reset ordering and descriptor bit2
as the source of the payload-processing gate. Auxiliary binding and automatic
clock semantics remain open. This supersedes the prior offset-only owner lead,
but does not establish live player identity. Documentation-only; last suite446.


## Auxiliary animation binding variants and cache lifetime

Decoded four flag-pair salts, key-only unsigned lookup, unused-list reuse and the
65535 individually-destroyed allocation path. Builder prefix confirms key and flag
storage; remaining mapping logic and flag meanings remain open. No fabricated
rig mappings added. Static documentation pass; last suite remains 446 tests.


## Executable paired binding-index operation

Recovered first-flag-gated sequential low12 swaps across eight mapping pairs,
preserving high4 bits and skipping absent members. Added a standalone validated
kernel with tests for preservation, overlap order, sentinel and alias behavior.
Pair identities and flag semantics remain unresolved; no rig table synthesized.

Validation: 449 tests pass; packaging, source hashes and local links pass.


## Binding class-to-mask conversion

Added recovered class1/2/3 to mask conversion with native five-bit shift counts
and sixteen-bit result truncation. Tests cover preserved nonclass words, shift
boundaries and non-idempotent repeated conversion. Class meanings and indices
remain caller-supplied; no inferred rig data added.

Validation: 452 tests pass; packaging, source hashes and local links pass.


## Hash-level animation binding map

Decoded type conversion, four paired hashes across two type groups, three mask
index producers, target remap fields and insertion-prefix updates. The executable
swap/mask kernels now have documented hash-level upstream contracts. Human joint
names, data producers and live rig selection remain open. Static documentation
pass; last full suite remains 452 tests.


## Named channel cross-check for binding masks

Matched five branch hashes to existing CRC-verified rig spellings: feet, hands
and Reference. Added a payload-free machine-readable catalog with source hash
and evidence limits. This supplies names for mask-group producers but does not
establish group=bone or variant=mirror. Eight special swap hashes remain unnamed.
Documentation/data pass; last full suite remains452 tests.


## Binding record encoding and inspection API

Added executable type conversion, four-byte main record packing and field
inspection with remap/Reference-bit boundary tests. A dedicated guide supplies
runnable synthetic examples and distinguishes main records from special mapping
swap/mask words. Full target matching and rig integration remain unresolved.
See docs/reconstruction/ANIMATION_BINDING_API.md.

Validation: 455 tests pass; packaging, source hashes and local links pass.

## Evaluator sample preparation

Static inspection recovered two distinguished-channel identity comparisons and
presence/cache masks for ten channel pairs. Documented eligibility, compact
sample ordering, exact tolerance, sentinels and initialization assumptions in
ANIMATION_EVALUATOR_PREPARATION.md. Pair identities and later cache consumers
remain open. No runtime implementation changed after the 455-test checkpoint.

## Animation endpoint motion

Decoded the next initializer stage: start/end samples, 60-unit sampling hints,
four-lane displacement, conjugate-start times end rotation, variant sign changes
and reciprocal-square-root refinement. Added a caller-sample numerical API and
four boundary/order tests. Also documented a separate initial-pose pair table.
Compact-cache consumers and physical root-motion application remain unproven.

Validation: 459 tests pass; packaging and local links pass. No live test run.

## Endpoint fallback channel selection

Decoded the hash-zero lookup used without an auxiliary binding. Added unsigned
lower-bound/type matching and endpoint source-selection helpers. Four tests cover
duplicates, first match, hash boundaries, absent binding versus missing channel,
and public adapter validation. Root-bone identity remains unresolved.

Validation: 463 tests pass; packaging, hashes and local links pass.

## Animation alternate-resource routing

Recovered the channel hash exclusions and wrapping reserved range in the sampling
predicate. Added routing inspection helpers and three tests. Hash-zero endpoint
fallback channels use the ordinary decoder even with an alternate resource.
The predicate's true result for missing metadata or out-of-range indices is
preserved and explicitly distinguished from channel validity.

Validation: 466 tests pass; packaging, hashes and links pass. No live sampling.

## Recursive animation sampling dispatch

Decoded the alternate wrapper's recursive routing, unchanged channel/time,
shared output/hint/cursor pointers, forwarded extra byte and terminal descriptor
width. Added a callback-based adapter with explicit cycle/bounds safeguards and
four synthetic tests. Actual descriptor decoding remains caller supplied; the
direct endpoint branch still uses explicit width 16.

Validation: 470 tests pass; packaging, hashes and local links pass.

## Animation descriptor registration catalog

The frozen descriptor table is empty, so inspected its initializer instead.
Recovered 72 explicit encoding-to-descriptor registrations with output widths
and sampling callbacks. Published a payload-free catalog and inspected encoding
zero's quaternion sampling path. This creates direct decoder entry points;
full interpolation/key-selection fidelity and live registration remain open.
No runtime code changed; last full suite remains 470 passing tests.

## Byte-time key selection

Recovered the encoding-zero sampler's cursor helper: implicit initial zero,
unsigned hint, forward scan, rewind upper bound and packed current/next ticks.
Added an executable helper and five tests, including an independent bisect oracle
across 2,313 hint/cursor combinations. Other timestamp selectors and interpolation
remain open; no game payloads used.

Validation: 475 tests pass; packaging, hashes and local links pass.

## Encoding-zero quaternion interpolation

Recovered and implemented source-copy, polynomial and near-aligned quaternion
sampling branches with explicit float32 operation order. Kept general blend
behavior unchanged. Documented injected versus scalar reciprocal seeds and the
unresolved runtime tick-scale producer. Four synthetic tests cover branch behavior
and safeguards; full channel decoding remains incomplete.

Validation: 479 tests pass; packaging, hashes and local links pass.

## Connected encoding-zero decoder

Traced reciprocal-time scalar initialization to float32 1/60. Connected channel
byte parsing, key selection, time clamping, quaternion interpolation and recursive
resource dispatch through an encoding-zero decoder callback. Five synthetic tests
include a full dispatch-to-pose-value path. No private-clip/native comparison;
other encodings, rig selection and physical motion coupling remain open.

Validation: 484 tests pass; packaging, hashes and local links pass.

## Encoding-27 vector decoding and corpus comparison

The representative corpus contains no encoding-zero tracks. Prioritized encoding
27 instead: recovered twelve-byte vector stride, four-byte alignment, linear
float32 sampling and cleared fourth lane. Connected it to resource dispatch.
Compared 5,845 samples from 835 reserialized private decoded tracks against the
prior reference; maximum component difference 9.5367431640625e-07. Original-byte
container extraction and native parity remain unverified. Only aggregate receipt
is public; three new synthetic tests cover decoder and dispatch boundaries.

Validation: 487 tests pass; packaging, hashes and local links pass.

## Original serialized channel check

Added a bounded byte-time serialized-record adapter for encodings zero and 27,
retaining opaque allocation metadata and copying sample bytes without decoding
and re-encoding. Original private slices supplied 506 encoding-27 tracks across
six clip bodies. All lengths matched recorded boundaries; 3,542 sample comparisons
had maximum component difference 9.5367431640625e-07. Published hashes and aggregate
counts only. Native execution, fresh archive extraction and full container parsing
remain separate. Three synthetic adapter tests cover padding, offsets and rejection.

Validation: 490 tests pass; packaging, hashes and local links pass.

## Encoding-21 packed rotations

Recovered the two-byte Z/W quaternion layout from single and paired decode paths.
Connected it to byte-time sampling, serialized adaptation and resource dispatch.
Validated 170 original serialized tracks with 1,190 reference comparisons; maximum
sign-invariant component difference 1.1199491845026444e-07. Published aggregate
receipt only. Three synthetic tests cover packed bits, dispatch, rewind and bounds.
Other rotation encodings and full rig selection remain open.

Validation: 493 tests pass; packaging, hashes and local links pass.

## Encoding-9 general quaternion decoding

Recovered ten-bit components, omitted xyzw insertion and reciprocal-refined
square-root arithmetic from single and paired helpers. Connected byte-time
sampling, serialized adaptation and dispatch. Original slices supplied 127 tracks
and 889 comparisons, maximum sign-invariant component difference
1.25930273264796e-07. Three synthetic tests cover omitted positions, field order,
seed policy and general rotations. Native parity and full rig selection remain open.

Validation: 496 tests pass; packaging, hashes and local links pass.

## Repeatable animation corpus inspection

Added a payload-free CLI/API for supported-record parsing and cached/reset sample
consistency. Six original extracted bodies contain 1,052 tracks: 803 validated,
249 unsupported, no shared records and no failures across 5,621 sample checks.
Encoding 12 accounts for 141 unsupported tracks and is the next targeted blocker.
This is scoped corpus coverage, not engine coverage or native equivalence. Three
synthetic tests distinguish supported, unsupported/shared and invalid records.

Validation: 499 tests pass; packaging, hashes and local links pass.

## Encoding-12 48-bit quaternion decoding

Recovered six-byte stride, two-byte alignment, fifteen-bit component scale and
omitted-component selection from the first two word high bits. Added the decoder
to serialized adaptation, dispatch and corpus inspection. All 141 new tracks pass,
raising this corpus to 944/1,052 supported tracks and 6,608 consistency checks.
No new independent-reference/native comparison claimed. Two synthetic tests cover
selectors, unused bit and integrated decoding.

Validation: 501 tests pass; packaging, hashes and local links pass.

## Encoding-12 reference comparison and threshold audit

Compared every key and interval midpoint on 141 original serialized tracks:
9,689 samples. Key-time error stays below 1.046e-7, but four midpoint comparisons
cross the source-copy threshold differently from the older host-double reference;
maximum difference is 0.0002589571241477101. Recorded aggregate outlier diagnostics
and added an exact float32 epsilon boundary regression. Preserved the recovered
branch instead of tuning to the old reference. Native seed parity remains open.

Validation: 502 tests pass; packaging, hashes and local links pass.

## Bit-mask animation timestamps

Decoded encoding-14's mask selector and verified the byte population-count table.
Implemented shifted bit search, clamped unsigned hints, rank and packed endpoints.
Four tests include 520 expanded-key oracle comparisons. Full encoding-14 decoder
integration remains next; corpus coverage has not increased in this pass.

Validation: 506 tests pass; packaging, hashes and local links pass.

## Encoding-14 mask-time sampling integration

Connected mask selection to 48-bit quaternion sampling and resource dispatch.
Added serialized mode/mask parsing with population-count validation and taught
the corpus probe to derive mask-track duration correctly. All 24 new original
tracks pass, yielding 968/1,052 supported tracks and 6,776 consistency checks.
Two synthetic tests cover cursor independence, shifted timing and malformed counts.
Independent numerical/native validation remains open for this encoding.

Validation: 508 tests pass; packaging, hashes and local links pass.

## Encoding-23 mask-time restricted rotations

Joined the verified mask selector and two-byte Z/W value format through static
callback inspection. Reused the mask sampler with format-specific value stride.
All 17 original tracks pass, yielding 985/1,052 corpus tracks and 6,895 consistency
checks. Two synthetic tests compare equivalent byte/mask timelines and exercise
dispatch/truncation. No new native or independent-reference comparison claimed.

Validation: 510 tests pass; packaging, hashes and local links pass.

## Encoding-11 mask-time general rotations

Verified calls to the encoding-9 value decoders and four-byte mask-track alignment.
Added serialized adaptation, shared sampling and corpus support. All 15 original
tracks pass; corpus now supports 1,000/1,052 tracks with 7,000 consistency checks.
Two synthetic tests cover byte/mask equivalence, padding and dispatch. Independent
numerical/native validation remains separate.

Validation: 512 tests pass; packaging, hashes and local links pass.

## Encoding-24 three-float quaternion sampling

Verified paired and single value decoding, selector masks, retained low bits and
twelve-byte sample stride. Integrated serialized adaptation and dispatch. All
fifteen new tracks pass, bringing the six-body corpus to 1,015/1,052 tracks and
7,105 consistency checks. Three synthetic tests cover selector preservation,
rewind, dispatch and malformed inputs. Scalar reciprocal seeds remain substitutes;
no native parity is claimed. See the three-float sampler guide for pseudocode.

Validation: 515 tests pass; packaging, hashes and local links pass.

## Scalar animation channels 39 and 54

Recovered signed-byte float scaling and uint32 interpolation, including native
zero-extension after wrapped subtraction. Added descriptor-specific four-byte
dispatch and corpus inspection. All 28 new tracks pass; corpus now supports
1,043/1,052 tracks with 7,301 consistency checks. Three tests cover signed
extremes, rewind, integer rounding/wrap and failure atomicity. Channel semantics
and native output parity remain open. Scalar sampler guide includes pseudocode.

Validation: 518 tests pass; packaging, hashes and local links pass.

## Mask-time float formats and complete sample-corpus coverage

Verified encoding-26 quaternion decoder calls and interpolation constants, plus
encoding-29 vector interpolation and explicit fourth-lane clearing. Integrated
both formats with serialized adaptation and dispatch. All nine remaining tracks
pass, yielding 1,052/1,052 tracks and 7,364 consistency checks in six private
bodies. Two synthetic tests exercise shifted timelines, rewinds, dispatch,
truncation and nonnormalized vector output. This is not whole-engine coverage.
Documented why the existing marker-search extraction is not a general container
parser and the structural, shared-reference and binding work still needed.

Validation: 520 tests pass; packaging, hashes and local links pass.

## Structural clip-body framing

Added a bounded reader based on Studio's documented version-1/version-2 container
layout. It walks events and typed bindings without marker search, preserves
opaque metadata and unresolved shared references, and delegates supported channel
records to the existing decoder. Corpus CLI now accepts a body without a record
sidecar. All six original version-2 bodies match the previous extractor's 1,052
track boundaries and binding identifiers, with exact end consumption. Two contain
event tracks. Four synthetic tests exercise versions, events, every truncation,
wrong counts/types, trailing bytes and shared-reference preservation. Version 1
and shared references have no original-body validation yet; unknown channel
formats and event classes fail explicitly. No native playback proof claimed.

Validation: 524 tests pass; packaging, hashes and local links pass.

## Broad clip framing and decoder priorities

Separated serialized channel framing from value sampling. Bounded framing now
handles documented families and byte/wide/mask timestamps without asserting
value-decoder support. All 3,760 existing indexed bootstrap bodies parse exactly;
all are version 2 and none has a shared reference. 2,991 bodies contain only
currently supported value codec IDs, an eligibility count rather than sampling
proof. The receipt inventories missing codecs, prioritizing wide-time 13, 28 and
10. Three synthetic tests cover large wide counts, unsupported-but-framed values,
mask counts, malformed times and truncation. Outer index completeness remains
unverified; six-body sampling coverage is unchanged.

Validation: 527 tests pass; packaging, hashes and local links pass.

## Wide-time key selection and vector channels

Recovered selector 0x140d581f0 and encoding-28 runtime header, alignment and vector
sampling. Added short/extended counts, uint16 timestamps, cursor-aware upper-bound
selection and serialized adaptation. Three synthetic tests cover count 255/256,
300-key payloads, duplicate/maximum timestamps, rewinds and invalid inputs. All
12,515 original encoding-28 tracks across 706 indexed bodies pass 87,605 sampling
consistency checks. These are not native numerical comparisons. Wide quaternion
formats remain next; the prior inventory receipt is a historical framing snapshot.

Validation: 530 tests pass; packaging, hashes and local links pass.

## Wide-time quaternion formats 10 and 13

Inspected both callbacks through their final-key branches, verifying common
value helpers, alignment, interpolation constants and operation order. Integrated
32-bit and 48-bit quaternion values with the recovered wide selector and runtime
headers. Two synthetic tests cover byte/wide equivalence, rewind, registered
dispatch, truncation and extended count. Original inventory checks pass all
12,038 encoding-10 and 16,605 encoding-13 tracks: 200,501 sample consistency checks
with no failures. No native numerical parity is claimed; scalar reciprocal seeds
remain substitutes and existing reference discrepancies remain documented.

Validation: 532 tests pass; packaging, hashes and local links pass.

## Wide-time rotation formats 22 and 25

Verified full callbacks for restricted z/w rotations and three-float quaternions,
including final-key decoding and shared interpolation branches. Added both to
wide sampling, serialized adaptation, dispatch and corpus inspection. Expanded
existing synthetic cases cover byte/wide equivalence, rewinds and extended count.
All 6,292 encoding-22 and 862 encoding-25 original tracks pass 50,078 consistency
checks. Scalar reciprocal seeds and native-output validation remain open.

Validation: 532 tests pass with expanded cases; packaging, hashes and local links pass.

## Packed 64-bit quaternion family

Recovered logical high-word-first ordering, three twenty-bit fields, unused bits,
omitted-component selection and float32 reconstruction from paired/single helpers.
Verified matching interpolation sections in all three callbacks. Integrated byte,
wide and mask variants 15/16/17. All 1,266 original tracks pass 8,862 consistency
checks; two synthetic tests cover selectors, word order, ignored bits and timeline
equivalence. Scalar reciprocal seeds remain substitutes; no native parity claim.
Only formats 40, 41 and 66 remain unsupported in the indexed inventory, totaling
110 tracks. Inventory format eligibility is distinct from full sampling validation.

Validation: 534 tests pass; packaging, hashes and local links pass.

## Remaining indexed formats and full sampling sweep

Recovered scalar wide/mask formats 40/41 and opaque selected-key format 66. The
latter copies eight bytes without interpolation; preserved as uint64 bits rather
than assuming four signed components. Added descriptor widths, serialized layout
and dispatch. Two tests cover scalar timeline equivalence and opaque selection
independent of float time. Full indexed sweep passes every one of 654,190 tracks
in 3,760 bodies, totaling 4,579,330 seven-position consistency checks. No native
agreement or every-key coverage is claimed. Raw-channel-to-rig integration is next.

Validation: 536 tests pass; packaging, hashes and local links pass.

## Raw compressed channels to rig poses

Added explicit raw-body/decoded-rig pairing with identifier binding, compressed
channel sampling, bind-component fallback, scale and hierarchy propagation.
Auxiliary channels and unmatched transforms remain diagnostics; duplicate targets
and shared references require resolution. Four tests cover binding, scale,
hierarchy, rewinds, isolation and failure atomicity. Six original bodies paired
with both base rigs produce 60 poses/4,320 bones compared against the older
independent reference. Maximum local translation/rotation errors are 9.998e-8
and 1.155e-7; model errors are 2.488e-7 and 1.419e-7. This is not live pose proof.
Simulation animation graph/checkpoint integration remains pending.

Validation: 540 tests pass; packaging, hashes and local links pass.

## Raw channels in the simulation graph and replay

Added caller-private JSON bundle export and an explicit raw_channels sampling
policy. Existing graph/clip clocks, blends and crossfades now invoke registered
raw decoders; fresh cursors avoid hidden mutable cache state. Checkpoints include
resource content and clocks. Auxiliary/unmatched values remain standalone adapter
outputs rather than inferred gameplay inputs. Four tests cover JSON pose parity,
graph blending, crossfades, checkpoint continuation/replay and atomic rejection.
Six original clips each completed 30 ticks on an explicitly selected male rig,
with exact continuation/replay agreement and no incidents. This does not recover
original authored graph selection, procedural layers or root-motion ownership.

Validation: 544 tests pass; packaging, hashes and local links pass.

## Executable authored comparison predicates

Added recovered float32 scalar comparators and the verified 184-byte authored
record decoder. Graph scalar expressions can now apply comparisons to explicit
inputs; all-node validation rejects malformed inactive expressions. Destination
connections and active-child clocks remain designed behavior, not recovered
transitions. Three tests cover tolerance/rounding/unordered semantics, record
bindings and threshold-driven selection with retained clocks. Five saved authored
examples match expected predicates; 15 supplied sample evaluations complete.
Outgoing authored edges and captured-parameter timing remain unresolved.

Validation: 547 tests pass; packaging, hashes and local links pass.

## Runtime animation output addressing

Added the runtime output descriptor adapter with stored-order flattening, class
8/9 resolution, scalar and timeline reads, and explicit owner-before-read
evaluation. Four synthetic tests exercise multi-output nodes, empty nodes,
handle bit selection, callback ordering and invalid snapshot bounds. This
implements existing recovered rules; it does not close authored graph lowering.
The resource-handle initializer and three related functions were reread; their
key-copy and provider lookup behavior agree with the existing research.

Validation: 551 tests pass; packaging, hashes and local links pass.

## Runtime class-0 identity lookup

Traced the separate 128-bit identity-to-uint32 compile branch and implemented
its word-wise hash, triangular probing and failure-output distinction. The
compile adapter preserves class 0 and successful unique dependency insertion.
Original lookup execution matched 400 synthetic cases, including the original
division helper. Four tests cover lookup and compiler boundaries. The consumer
prepares a flagged parameter group before a guarded scalar read; map population,
group callbacks and flag reset remain open. No authored-to-runtime identity
join or input freshness claim is made.

Validation: 555 tests pass; packaging, hashes and local links pass.

## Parameter-group preparation and conditional reset

Located the reset loop in the animation update tail and joined it to the same
parameter context consumed by class-0 scalar reads. An accumulating branch
skips the reset. Registration creates a callback group, clears its prepared
flag, and maps successful identifier lookups to a byte-sized group index.
The portable API keeps reset selection explicit instead of assuming a tick
cadence. Original helper validation passed 48 calls and six isolated reset
blocks. Four tests cover shared groups, callback ordering and reset boundaries.
Concrete callbacks, map population and outer update scheduling remain open.

Validation: 559 tests pass; packaging, hashes and local links pass.

## Animation deferral gate and interface identity

Recovered pending-count, graph-state, mode-bit and byte-counter eligibility for
animation deferral, including wrap-before-compare and float32 accumulated time.
Connected update and registration to a constructed interface at owner+24;
its virtual update slot is 0x50. Added a pure branch planner, not an automatic
engine cadence. Original gate/effect blocks matched 400 synthetic cases, and
four tests cover branch and arithmetic boundaries. Registration also consumes
an incoming callable container; concrete callback classes remain unresolved.

Validation: 563 tests pass; packaging, hashes and local links pass.

## Named animation threshold producer

Connected GetUpdateThresholds registration, installer, concrete callback and
outer-update consumption. The callback's seventh byte directly supplies the
deferral threshold. Recovered defaults, two-component gate, three-bit table
selector and kind-40 override are executable without naming unknown fields.
Original callback arithmetic matched 400 synthetic cases with component/type
lookups stubbed. Four tests cover packet behavior and policy composition.
Component writers, source table population and scheduler caller remain open.

Validation: 567 tests pass; packaging, hashes and local links pass.

## KinoComponent update and clock source

Identified the threshold source type as KinoComponent and connected its stored
interface to the exact owner+24 factory result. Its update method conditionally
calls the recovered outer update. The animation-time task configuration supplies
a receiver-slot dispatcher, with worker selection and membership still open.
Recovered component flags, missing-owner/world behavior and owner bit58 clock
selection. Original selection matched 256 synthetic cases; four tests pass.
Rejected a same-offset serializer belonging to ProgressionCameraTransition.
Clock domains, threshold-field writer and physics-relative timing remain open.

Validation: 571 tests pass; packaging, hashes and local links pass.

## Concrete animation-time batch visitor

Closed the constructor/setup/table join for the animation-time job. The final
table selects the reverse visitor without pointer adjustment; it captures its
callback once and reads receivers at invocation time. The earlier adjusted
visitor was a different candidate and is explicitly superseded. Original visitor
and receiver dispatcher matched 36 synthetic cases, including mid-batch callback
and entry replacement. Four tests cover the portable boundary. Actual membership,
clock producers and cross-job dependencies remain open.

Validation: 575 tests pass; packaging, hashes and local links pass.

## Animation registry copy into the job

Located the exact destination writer in the configured UpdatePreActionGather
task. It copies a source registry into the animation-time job, preserving source
order and pointer identity. Nonempty sources reset the active count; an empty
source skips that reset. The portable API retains this distinction and models
capacity reuse and inactive tail preservation. Original branch/field-update
instructions matched 180 synthetic cases with external helpers stubbed. Four
tests cover the API, including composition with the selected batch visitor.
Registry insertion/removal, surrounding destination reset and task dependency
edges remain open. No original-game pause/step control was attempted.

Validation: 579 tests pass; packaging, hashes and local links pass.

## Animation claims consume the gathered count

Joined the animation gather count to the selected range worker's atomic claim
field. Ordinary complete claiming supplies a path to zero without a separate
unconditional reset. Zero can precede context entry and receiver callbacks, while
queue-change yielding can preserve a positive remainder. The explicit claim API
returns a captured storage span with late entry reads. Original worker, selected
visitor and dispatcher matched 576 synthetic cases, including yield signals during
the first receiver call. Four additional tests cover claim/copy/visit composition.
Native contention, completion and cross-request storage exclusion remain open.

Validation: 583 tests pass; packaging, hashes and local links pass.

## Animation stage dependencies and ordinary reuse route

Recovered seven setup registrations from pre-action gather through character and
skeleton preparation to Kino pre-graph, then separate animation-time/interaction
branches reconverging at action gather. The animation job now joins the previously
verified downstream action/physics and ordinary EndFrame rearm route. This closes
the ordinary static reuse argument for this branch; live identity and exceptional
modes remain open. Original registration instructions matched the partial graph at
two synthetic owner bases with volatile-register clobbering. The runnable probe
uses synthetic bodies to demonstrate that zero remaining work does not release the
gather while animation dispatches remain unfinished.

Validation: 585 tests pass; packaging, hashes and local links pass.

## Animation event slot and registry removal

Joined the animation source to world event slot 16. Recovered removal's first-match
search and last-entry replacement, which can change the next batch's order while
leaving earlier gathered arrays untouched. Added the serial event-registry token
API with unique insertion and explicit slot bounds. Original indexed wrappers,
searches and erase helper matched 2,016 synthetic cases with external helpers
stubbed. Four tests cover slot isolation, uniqueness, removal/copy/visit composition
and adapter bounds. KinoComponent-specific activation and live player membership
remain unresolved; generic slot geometry is not a membership proof.

Validation: 589 tests pass; packaging, hashes and local links pass.

## KinoComponent descriptor routes

The world constructor explicitly binds KinoComponent metadata to an unconditional
slot-16 route and a separate fallback-22/conditional-23 route. The latter reads
the owning object's mode byte and selects 23 exactly when its low three bits equal
one. Generic removal covers both secondary candidates without reevaluating that
predicate. Original setup instructions produced both records, and the original
predicate matched all 256 mode bytes. Added route-selection/cleanup API and three
tests. The component-specific type route is now established; player context lookup,
lifecycle invocation and live batch identity remain open.

Validation: 592 tests pass; packaging, hashes and local links pass.

## Direct KinoComponent activation

Recovered the component's direct activation routine and its table callback, which
requests activation from component flag bit 26. Slot 16 is inserted only when the
owner context is absent from the time group's context lists; slots 17 and 19/37
are also registered. Disable removes both variants, with missing-world and repeated
request behavior retained. Added an explicit effect planner; opaque interface and
post-unregister calls remain visible. Original routine and context lookup matched
384 synthetic cases with external effects stubbed. Four tests cover transitions
and event-registry composition. Higher-level callers and live identity remain open.

Validation: 596 tests pass; packaging, hashes and local links pass.
