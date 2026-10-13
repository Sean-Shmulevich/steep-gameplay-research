# Current status

Snapshot: 2026-10-13. This page qualifies older reports. No audited percentage of the complete engine is available, and no percentage estimate should be treated as measured coverage.

| System | Established locally | Still open |
| --- | --- | --- |
| Snow and input shaping | Immersion/contact arithmetic, adhesion, density response, cookers, spring paths, multiple material/profile joins | Full active-branch coverage, action-vector writer/freshness, exact device-to-substep timing, terrain-wide selection |
| Body mass | One live main-body inverse mass agrees exactly with the decoded hull-volume/density calculation | All body representations, combined rider mass, later state-dependent changes |
| Tricks | Proposal arithmetic, ski axis remapping, assistance and reset paths, entity target publication | Final player-body actuation through other components/children; universal spin/flip behavior |
| Animation | Representative decoded-clip research, playback/blending kernels, graph scalar production, compiled-key to provider-key assignment, palette production and joint-remap fallback | Authored UID to compiled key, active rig addon merge, active landing selection, packed buffer conversion and full procedural scheduling |
| Contact and landing | Selected profile-to-force path, timer and cached-flag writers, observed moving-player contact transitions | Complete landing/crash classifier and exact update order |
| Walking | Configuration and animation metadata leads | Movement-speed consumers, snow-depth effects, active controller ownership, root-motion/IK coupling |
| Time and weather | Controller ownership, clock progression and gates, weather interpolation, ordered preset blending | Concrete track evaluator/time encoding, remaining selection, visual/physical wind joins, weather-to-grip effects |
| Camera and air sports | Many local filters, force/control formulas, selection and projection paths | Final integration, full environmental zones, comprehensive live validation |
| Scoring | Local formulas, thresholds, history and attribution paths | Complete detector coverage and event commit/cancel behavior |

## Corrections worth preserving

- The normal/fast control blend uses projected runtime speed multiplied by3.6 against7 and12. The initial7–12m/s description was misleading.
- Rock and ice can have profiles in the same fluid-contact system. Zero immersion alone is not a universal airborne flag.
- Rider tuning mass20 does not establish the main body's mass. The observed hull-backed body matched mass approximately5.688 in the recovered convention.
- A modal collision-mask key is not a selected material pointer.
- The factory function initially described as an animation clone registers object identity. A separate real clone passes a source member into a handle initializer. The full resource-key join remains open.
- A recovered quaternion-error/dt physical pose follower is not yet proved to drive the main player's trick body.
- Copying a trick target to entity transforms does not establish that it is purely visual. Other component and child receivers remain unresolved.

## Latest runtime evidence

[The moving-rider capture](validation/contact-motion.md) recorded767 complete guarded observations across approximately1.96seconds. Body translation changed, activity remained enabled, and sampled contact changed from absence to contact return and back to absence. All sampled skip values agreed with the decoded absence threshold.

This did **not** prove same-substep execution. The95th-percentile group interval was14.77ms and the maximum gap40.8ms, exceeding the test's timing criterion. Its online event detector reported false because it expected contact→absence→reset and the recording began in absence. That flag must not erase the observed contact return.

The subsequent automated Space attempt never reached gameplay: startup/control helpers timed out and the bounded launcher cleaned up. No Space-driven jump result exists from that attempt.

## Most useful next work

1. Arm the recorder before an ordinary input command; preserve before/after history and reduce measured sampling gaps.
2. Finish the authored animation identity-to-runtime handle join, then trace landing selection.
3. Follow child/component trick target consumers to the actual physical body or classify their other role.
4. Trace the shared action-vector writer and publication generation; the concrete snow callback now joins the motion action store.
5. Recover the environment track evaluator's clock conversion.
6. Establish a separate on-foot controller path before applying the testbench to walking.

These are research priorities, not claims that the relevant implementation is already recovered.

## Reconstruction-focused review

Five focused investigations checked skeletal joins, animation providers, asset interfaces, scheduler contracts and the snow input callback. See [reconstruction and probes](reconstruction/MODDING_AND_PROBES.md) and the research links in the [implementation guide](ENGINE_RECONSTRUCTION.md). The overview previously overstated the final-palette gap; the existing skinning chapter already closes its local arithmetic. These checks did not launch the game or prove complete engine parity.

## Scheduler reconstruction update

The [smoothing audit](reconstruction/SCHEDULER_SMOOTHING_AUDIT.md) supplies the complete local ring/table arithmetic, now implemented in the independent engine. The [constructor audit](reconstruction/SCHEDULER_LIFETIME_AUDIT.md) establishes the inspected timing object's startup values and ten-entry allocation.

The [input audit](reconstruction/SCHEDULER_INPUT_AUDIT.md) closes a conditional static chain from the registered pre-simulation motion batch through `BeforeSimulation` to `PhysicsWorldStep`, including a callback route to player action ingestion. This narrows the earlier statement that ingestion placement was wholly unresolved. It still requires current selected-player membership, matching request identity and a proved sample writer before claiming exact input age or ordering for a captured player update.

The manager constructor's final setup helper was checked and does not establish a sample commit. Context/binding population remains the concrete writer lead. Native pause/step remains gated on owner lifetime and exclusion of new submissions. See the [current scheduler roadmap](../engine/SCHEDULER_ROADMAP.md).

The subsequent [action-publication follow-up](reconstruction/ACTION_PUBLICATION_FOLLOWUP.md) found binding insertion and a reset write to the sampled action vector. The later callback audit below resolves three repopulation paths; active selection and sample-generation semantics remain unresolved. The [membership follow-up](reconstruction/SCHEDULER_MEMBERSHIP_FOLLOWUP.md) found that an empty registration source retains the prior gathered array; current membership requires a reset/request join. The [submission follow-up](reconstruction/SCHEDULER_SUBMISSION_FOLLOWUP.md) traced teardown but did not establish exclusion. These narrow the remaining questions without claiming native deterministic stepping.

The [action callback audit](reconstruction/ACTION_RESET_CALLBACK.md) subsequently resolved repopulation for three constructed action types, including a two-axis formula. Runtime player type and device timing remain open. The [batch epoch audit](reconstruction/SCHEDULER_BATCH_EPOCH.md) explains how fully claimed batches leave zero active count despite retained storage. The [backend completion audit](reconstruction/BACKEND_COMPLETION_FOLLOWUP.md) closes a normal queued-callback decrement path. Neither zero claims nor that selected-group decrement establishes global quiescence; [optional child lifetime](reconstruction/SCHEDULER_CHILD_LIFETIME.md) still lacks a concrete submission-exclusion join.

The [default processor](reconstruction/ACTION_PROCESSOR.md) is now recovered as pass-through, with an explicit composed action API. Configured alternatives and active player selection remain open. [Backend worker registration](reconstruction/BACKEND_WORKER_REGISTRATION.md) connects the queued consumer through its manager-wait wrapper and descriptor entry bridge, while protected platform launch and lifetime remain unresolved. [Child-type research](reconstruction/PHYSICS_WORLD_CHILD_TYPES.md) rules out the ordinary 40-byte component reader as the missing factory source.

The [rearm audit](reconstruction/SCHEDULER_REARM.md) establishes reservation-before-worker accounting and worker-return-before-ordinary-successor-release. The action graph's conditional entry and terminal nodes are identified. Its next-request external submission gate remains the missing storage-lifetime join; this is narrower than an unknown generic job scheduler.

The [outer caller audit](reconstruction/ACTION_REARM_CALLER.md) connects the action graph to an eligible-world chain and `Engine::EngineLoop::Step`, then follows cached terminals into preparation/root submission. The remaining exclusion question is the outer completion handshake before preparation runs again. [Alternate release](reconstruction/ALTERNATE_DEPENDENCY_RELEASE.md) is now decoded as recursive hold removal without job execution or started-request acknowledgement. [Executable request rules](reconstruction/REQUEST_STATE_MODEL.md) preserve the local counter and credit branches with 14 new tests. These are static and independent-reference results, not native pause/step validation.
