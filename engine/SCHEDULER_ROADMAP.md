# Scheduler reconstruction and modding release gates

Scheduler reconstruction is the current primary goal. The independent runtime remains the testbed; extending rendering and general gameplay takes second priority. This is a sequence of evidence gates, not a percentage estimate.

## Closed in this pass

- Recovered smoothing history, chronological float32 mean, frequency table, accumulator cap, policy override and subdivision decisions are executable. Each frame exposes its plan and retained time.
- Static registration joins one motion-processing batch through `PreBeforeSimulation` and `BeforeSimulation` to the world step. Current selected-player membership and request identity are still required before applying that edge to a live player.
- The timing constructor's ten-entry allocation and initial timing values were traced. Startup values do not imply that a substep has executed.
- The owned runtime records input publication, frame plans, substep entry, physics completion, animation completion and state publication. Traces identify invocation and frame, retain records without wrapping, and report dropped events.
- Headless experiments control inputs and frame intervals and check complete owned-state replay. They do not send OS input or attach to the original executable.

See [smoothing audit](../docs/reconstruction/SCHEDULER_SMOOTHING_AUDIT.md), [input-order audit](../docs/reconstruction/SCHEDULER_INPUT_AUDIT.md), and [constructor/lifetime audit](../docs/reconstruction/SCHEDULER_LIFETIME_AUDIT.md).

The standalone owned dependency executor also distinguishes claimed from completed work, retains claimed callbacks, blocks unsafe replacement while work is outstanding, and requires matching callback version tokens for quiescent restoration. It is a designed reference API; gameplay phases are not yet dispatched through it.

## Next gates

1. **Active membership and request identity.** Join the selected player's motion object to the specific pre-simulation batch, scheduler/world instance and submitted request. A constructor dependency alone does not prove membership. The [membership follow-up](../docs/reconstruction/SCHEDULER_MEMBERSHIP_FOLLOWUP.md) shows that an empty registration source preserves old gathered contents, so destination reset/request history is also required. Reacquire process-specific identities for any separately authorized live check.
2. **Input freshness.** The [action follow-up](../docs/reconstruction/ACTION_PUBLICATION_FOLLOWUP.md) now joins a binding-refresh reset to the sampled action vector. Three repopulation callbacks and the fallback processor are now resolved. Establish the active binding, configured processor if present, and source publication protocol. Match a produced sample to the consuming invocation. Equal values, input delivery time and consecutive-nonzero counters are insufficient.
3. **Owner lifetime and submission exclusion.** The [submission follow-up](../docs/reconstruction/SCHEDULER_SUBMISSION_FOLLOWUP.md) closes the cleanup chain and shows the later backend lock cannot cover earlier scheduler destruction. Resolve the two virtual children destroyed before manager cleanup, then join their behavior to submission callers. Existing drain observations cannot establish this alone.
4. **Original execution oracle.** Once safe observation boundaries are established, record matched entry/exit events and dependency identities with drop accounting. Compare the original selected substeps and publication order to reconstructed plans. Keep independent thread timelines distinct until causality is established.
5. **Native pause/single-step proof.** Require exclusion of new submissions, completion of claimed work, valid owner lifetime and required thread/TLS context before attempting scheduler control. First success must survive repeated pause/step/resume and world changes without a stale callback or deadlock.
6. **Modding release.** Publish stable owned handles, phase-specific mutation rules, callback version identity, failure containment and reproducible mod state. Original-process mod support requires the native gates above; an independent engine API does not imply it.

## Reproduce a scheduler experiment

```sh
python3 -m engine.experiments engine/examples/scheduler_probe.json --output /tmp/scheduler-report.json
```

The example varies outer frame intervals, commits steering/jump/flip inputs and includes an 80 ms stall. It uses synthetic terrain. The recorded validation ran 171 frames and 280 substeps, matched the replay state hash, and retained all 1,636 trace records with zero drops. Frequencies selected during that run included 90, 100, 105, 110 and 120. The stall retained its raw interval in smoothing history while capping consumed accumulation to approximately 66.67 ms.

`GET /trace` exposes the local inspector's trace. `frame_planned` is a decision, not an execution receipt. `substep_committed` commits that local substep, but an enclosing `frame_aborted` invalidates the entire frame's state changes. The trace preserves these failed attempts for diagnosis. Restoring a checkpoint restores its trace branch. Trace contents do not enter the simulation state hash, and losing trace capacity does not alter physics.

The current trace is serial and belongs to our implementation. It does not establish original thread order, native cache-swap cardinality or input age. Release claims must name which implementation and which gate passed.

## Owned pause/step checkpoint

The Python `SchedulerController` now implements an explicit submission gate with generation-qualified pause tokens. It distinguishes one fixed developer tick from one scheduled outer frame. Threaded tests cover a competing submitter, and a 200-frame paused-stepping check completed 300 substeps with exact replay agreement, a rejected stale token after restore and no trace drops. This proves the owned controller's tested contract, not native exclusion.

## Further static closures

- [Action callbacks](../docs/reconstruction/ACTION_RESET_CALLBACK.md): three constructed-and-inserted action types repopulate cleared samples. One exposes the full two-axis combination/publication formula. Its magnitude is not a generation counter. Player subtype, optional processor and source timing remain open.
- [Batch epochs](../docs/reconstruction/SCHEDULER_BATCH_EPOCH.md): the gathered count is consumed before callbacks. A fully claimed prior batch makes retained empty-source storage inactive; early exits and in-flight callbacks still require a cross-request protocol.
- [Child lifetime](../docs/reconstruction/SCHEDULER_CHILD_LIFETIME.md): the earlier child slots start null and are cloned polymorphically. Their concrete source types remain unresolved, and optional children cannot be assumed to provide a universal scheduler barrier.
- [Backend completion](../docs/reconstruction/BACKEND_COMPLETION_FOLLOWUP.md): the queued callback branch decrements not-started before the callback and outstanding after normal return. Concrete consumer registration was subsequently joined through the descriptor bridge below. Notification and whole-engine exclusion remain unproved.

The next native work should resolve the active action processor/source producer and the component request/rearm contract. Neither more owned-runtime pause features nor interpreting a zero claim count as completion would close those native gaps.

## Processor and worker-entry follow-up

The [default processor audit](../docs/reconstruction/ACTION_PROCESSOR.md) closes the fallback processing method as a four-lane copy with a first-use marker. The composed action API now requires callers to distinguish fallback, bypass and an externally evaluated configured processor.

The [worker-registration audit](../docs/reconstruction/BACKEND_WORKER_REGISTRATION.md) joins setup's callback address through a descriptor entry bridge and shared-manager wrapper to the queued backend consumer. Protected platform launch/notification and manager lifetime remain unresolved.

The [child-type follow-up](../docs/reconstruction/PHYSICS_WORLD_CHILD_TYPES.md) rules out the component's ordinary fixed-size deserializer as the source of optional child instances. Type resolution now requires out-of-line linkage or a runtime assignment writer. Repeating the ordinary reader would not close that gap.

The [rearm audit](../docs/reconstruction/SCHEDULER_REARM.md) now connects ordinary queue reservation to execution and finalization. Execution accounting begins before the fetched job reaches its worker, and ordinary successor release waits for returned worker bodies. It also identifies the action graph's conditional entry and terminal nodes. The next decisive join is the external caller that rearms that specific graph after prior storage users have returned, including early-exit requests.

## Outer action-chain and request rules

The [caller audit](../docs/reconstruction/ACTION_REARM_CALLER.md) now joins the world action wrapper to an eligible-world chain, the bound `Engine::EngineLoop::Step` callback, cached stage terminals, preparation and root submission. Preparation clears topology without a local worker wait. The next gate is the outer engine-loop completion/event handshake before repeated preparation and submission.

The [alternate-release audit](../docs/reconstruction/ALTERNATE_DEPENDENCY_RELEASE.md) resolves how unselected routes remove holds recursively without beginning jobs or acknowledging requests. A terminal reached by this route is not an execution-completion receipt.

The [request-state reference](../docs/reconstruction/REQUEST_STATE_MODEL.md) makes local request, hold and credit rules executable with explicit unresolved callback effects. Fourteen boundary tests pass. This reference does not add native control or replace the owned dependency executor. Indexed registry insertion and duplicate-pointer checking are also known; player registration with selector 24 remains open.

## Ordinary frame rearm now joined

The [EndFrame audit](../docs/reconstruction/ENGINE_LOOP_HANDSHAKE.md) closes the ordinary action-receiver completion → downstream dependencies → EndFrame callback → preparation → next-root submission path. This supersedes the wholly unresolved outer caller in the preceding section. It protects the stated ordinary receiver-storage ordering; it does not make EndFrame a universal idle point. Next-root submission can occur before EndFrame's own final bookkeeping.

The [root route](../docs/reconstruction/ENGINE_ROOT_STEP_ROUTE.md) identifies mode gates, the Step rebuild gate and world-stage endpoints. Two provider entry/terminal interiors remain unresolved. The [event branch](../docs/reconstruction/ENGINE_EVENT_SUBMISSION.md) bypasses root submission and uses an engine-owned handle also touched during restart; the platform operations and exact waiter remain open. The [explicit helper audit](../docs/reconstruction/WAIT_HELPER_DISPATCH.md) also closes accounting-before-worker for the second inspected dispatcher.

Next native targets, in order:

1. Mode-byte writers and the exact event-handle consumer: determine who requests the alternate end-frame path and what completion they observe.
2. Both provider entry-to-terminal interiors: establish the outstanding dependency chains rather than treating endpoints as complete jobs.
3. Active world/player/request identity and source-input freshness, followed by a bounded original execution trace when its observation contract is ready.
4. Native control only after owner lifetime, submission exclusion and required thread context are established for that specific operation.

The [alternate-propagation reference](../docs/reconstruction/ALTERNATE_DEPENDENCY_MODEL.md) adds executable branch bypass with ten synthetic tests. It complements local request/credit rules; a complete mixed normal/alternate scheduler interpreter remains to be implemented and checked against native evidence.
