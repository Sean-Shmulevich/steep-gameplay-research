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

1. **Active membership and request identity.** Join the selected player's motion object to the specific pre-simulation batch, scheduler/world instance and submitted request. A constructor dependency alone does not prove membership. Reacquire process-specific identities for any separately authorized live check.
2. **Input freshness.** Trace the concrete action-payload writer and its publication protocol. Match a produced sample to the consuming invocation. Equal values, input delivery time and consecutive-nonzero counters are insufficient.
3. **Owner lifetime and submission exclusion.** Identify who prevents new submissions and retains the scheduler, work arrays and already-claimed callbacks. Existing drain observations cannot establish this alone.
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
