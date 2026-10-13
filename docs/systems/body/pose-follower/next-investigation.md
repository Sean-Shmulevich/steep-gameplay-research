> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Next step

Choose a further static binary trace before a new live rotation test. The exact physical consumer of the player's procedural target is missing, and the recovered follower currently has indexed physics-pose body ownership.

## Decisive binary trace

Resolve the owning entity's concrete target-publication callback, then follow its matrix argument to the main snow-body identity or a physical target/constraint driver. The producer, virtual slot and candidate final consumers are named exactly in [private/EVIDENCE.md](evidence.md), P1, P2 and P5.

Start from the player's constructor-backed actor/entity ownership, not a general search for angular arithmetic. Recover at most eight constructor-backed entity vtables. Inspect only their target-publication slot, then export at most twelve concrete consumers, each with the existing 24 KB function-size cap. Follow at most two indirect dispatch levels. Verify every selected instruction against the image.

Stop successfully when the submitted target matrix is shown to reach the same runtime/body ownership chain as the guarded main-body angular field, with update gates and assignment/impulse/constraint semantics. A callback that only updates entity transforms or render state is also a decisive result for that callback. Stop with an explicit unresolved edge if no concrete vtable binding is found or the bounded candidate budget is exhausted. Do not infer main-body selection from the presence of the follower elsewhere in the binary.

## One deferred testbench experiment

Question: during one controlled pure-axis trick and its release/landing, do physical body orientation and angular velocity follow the controller target, or does visible rotation continue primarily through procedural/clip pose after physical motion has stopped?

This is proposed, not run. Preconditions are the completed callback/body join above and safe read-only access to each selected source. A human starts the game, chooses one recorded sport/stance, resets to the same launch location and heading, confirms camera and controller state, and performs all input. Reset through the game's ordinary controls; preserve a record of input values rather than assuming identical body pose implies identical initial state.

Use one session with three bounded segments: 2 seconds of no-input baseline, a single 0.5-second human-held pure-axis rotation command followed by 1 second of release, then capture through the first landing/reset for at most 5 further seconds. If the no-input baseline cannot reach the same relevant airborne/controller state, record that and do not treat it as a matched flight baseline. Total capture budget is 10 seconds, with a 12-second watchdog and no hooks or process-memory writes.

Discover objects by the existing root/player membership traversal. Check process creation identity, typed player, owner backpointers, entity/runtime/body links and the now-resolved target consumer. Bracket every payload batch with those identities. Do not scan arbitrary memory, reuse unchecked pointers or assume an animation graph's body is the main physical body. Reject changed identity, unreadable ranges or unsupported layouts.

Measure actual input XYZ and latches; proposal, accepted main vector, intensity, selected limit, auxiliary Z and assembled angular output; procedural target basis; physical body basis and angular XYZ; animation angular cache and selected clip identity/phase where safely resolved; active/frozen flags, contact timers and reset predicates. Record radians per simulation-time unit for body and target-derived rates, degrees only where that producer converts to degrees, clip phase as dimensionless and physical/target quaternion orientation in the established transform convention. Preserve any unresolved units as unresolved.

Aim for one guarded native request every 10 ms. Record each field's read timestamp and actual simulation timestep, not just request launch time. If median interval exceeds20 ms or a read bracket spans more than10 ms, the test cannot resolve the short contact/landing transition at the intended cadence. Never describe the samples as atomic. If the current transport cannot meet that budget, stop and improve the read-only batching offline before rerunning.

Discriminating outcomes:

- If target-derived orientation rate, physical body angular velocity and physical basis changes agree over sustained motion, that supports physical coupling in the tested branch. Compare in one proven frame and use simulation time. A one-sample match is insufficient.
- If the controller/visual pose rotates while the main body basis and angular velocity remain still, that separates visual or procedural turning from main-body actuation in the tested interval. An unmeasured physical rider body still remains possible.
- At release, a retained accepted vector supports the documented latch lifetime. A changed graph field alone does not establish a body reset.
- At landing, an observed body angular zero plus continuing target/clip rotation distinguishes the known physical reset from animation continuation. Guard changes, sequential-read races or a missed reset invalidate that conclusion.

Failure conditions include uncontrolled input/focus, unmatched state, unrecorded selected target branch, changed object identity, nonfinite poses, unresolved quaternion convention, cadence failure, landing outside the budget or no resolvable clip state. The test does not prove universal sport parity, full constraint behavior, deterministic replay or a conserved-momentum model. Exact video-frame alignment would require separate timestamp calibration; do not use the recorded video alone as timing proof.
