# Current status

Snapshot: 2026-10-13. This page qualifies older reports. No audited percentage of the complete engine is available, and no percentage estimate should be treated as measured coverage.

| System | Established locally | Still open |
| --- | --- | --- |
| Snow and input shaping | Immersion/contact arithmetic, adhesion, density response, cookers, spring paths, multiple material/profile joins | Full active-branch coverage, exact device-to-substep timing, terrain-wide selection |
| Body mass | One live main-body inverse mass agrees exactly with the decoded hull-volume/density calculation | All body representations, combined rider mass, later state-dependent changes |
| Tricks | Proposal arithmetic, ski axis remapping, assistance and reset paths, entity target publication | Final player-body actuation through other components/children; universal spin/flip behavior |
| Animation | Representative decoded-clip research, playback/blending kernels, graph scalar production, runtime handle initialization leads | Complete authored clip-to-runtime key join, active landing selection, full masks and procedural scheduling |
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
4. Trace the concrete input-manager vector callback into storage and sample freshness.
5. Recover the environment track evaluator's clock conversion.
6. Establish a separate on-foot controller path before applying the testbench to walking.

These are research priorities, not claims that the relevant implementation is already recovered.
