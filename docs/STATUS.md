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

Scheduler work is the primary reconstruction priority. The [current roadmap](../engine/SCHEDULER_ROADMAP.md) summarizes established evidence, unresolved boundaries and release gates.

The ordinary action-completion route now reaches the [EndFrame callback](reconstruction/ENGINE_LOOP_HANDSHAKE.md), which prepares dependencies and submits the next root. This is a conditional receiver-storage ordering, not global quiescence: EndFrame can still have positive dispatch accounting when it submits that root. [Root-to-Step routing](reconstruction/ENGINE_ROOT_STEP_ROUTE.md), [mode copies and writers](reconstruction/ENGINE_MODE_WRITERS.md), and both [AI provider chains](reconstruction/ENGINE_PROVIDER_CHAINS.md) have concrete static relationships.

The engine-owned [event consumer and stop request](reconstruction/ENGINE_EVENT_CONSUMER.md) join restart, end-frame notification and the outer caller sequence. Protected platform operations, the outer interface callback and destruction remain unresolved. No safe native pause/step API is claimed.

The [mixed scheduler reference](reconstruction/MIXED_SCHEDULER_IMPLEMENTATION.md) combines range, callback, terminal and conditional jobs with immediate normal/alternate dependency effects. Its synthetic three-cycle probe preserves EndFrame overlap and a skipped middle route. The full independent suite passes 407 tests. Native thread context, concurrent queue operations and dynamic graph rebuilding remain outside that model.

The input investigation has recovered [repopulation callbacks](reconstruction/ACTION_RESET_CALLBACK.md), two-axis publication and the [fallback processor](reconstruction/ACTION_PROCESSOR.md). Runtime player selection, configured alternatives and source freshness remain open. [Indexed membership](reconstruction/SCHEDULER_MEMBERSHIP_FOLLOWUP.md) and [batch consumption](reconstruction/SCHEDULER_BATCH_EPOCH.md) are known, but the selected player/world/request join still requires current identity evidence.

These scheduler passes were static analysis and independent implementation. They did not launch, attach to or control the original game. Test counts and graph connectivity are not original-engine fidelity percentages.

Optional [mixed gameplay dispatch](reconstruction/GAMEPLAY_JOB_INTEGRATION.md) now executes real phase work, preserving direct-path state hashes, replay and rollback across all five sports. Its graph is explicitly designed; this does not recover native gameplay topology. The [outer-interface candidate](reconstruction/ENGINE_OUTER_INTERFACE.md) and [owner-destruction boundary](reconstruction/ENGINE_OWNER_DESTRUCTION.md) document useful native leads without claiming the missing caller or teardown identity.

The [queue audit](reconstruction/SCHEDULER_QUEUE_ELIGIBILITY.md) corrects the earlier category count and separates job eligibility from occupancy scoring. Its selection arithmetic now runs in the optional [queue policy model](reconstruction/QUEUE_POLICY_MODEL.md), with explicit category and mask inputs. [Producer findings](reconstruction/SCHEDULER_QUEUE_PRODUCERS.md) establish worker-count defaults and required-mask routing. [Trace analysis](reconstruction/TRACE_ANALYSIS.md) now correlates owned execution attempts and rollback without equating complete evidence with successful execution.
