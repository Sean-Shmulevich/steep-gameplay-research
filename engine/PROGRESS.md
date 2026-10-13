# Reconstruction progress and next work

Status: active implementation. Scheduler reconstruction is now the main priority; see [release gates and experiments](SCHEDULER_ROADMAP.md). The requested full reconstruction is not complete. This file is the continuation point across implementation passes; do not restart or replace the existing prototypes casually.

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
