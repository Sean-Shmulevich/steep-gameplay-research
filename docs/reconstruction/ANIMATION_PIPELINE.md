# Animation reconstruction contracts

This is a proposed implementation sequence grounded in the [animation findings](../systems/animations/OVERVIEW.txt). It does not supply authored poses or establish every active graph branch.

## Pipeline and ownership

1. Asset adapter resolves patched IDs and converts clip time into an explicit clock domain. Output immutable channel metadata and locally supplied samples.
2. Binding maps channel IDs to skeleton joints or auxiliary outputs. Missing bindings produce diagnostics. Never equate track count with bone count.
3. Playback owns phase, marker coordinates and transition state. Preserve inclusive wrap endpoints: exact phase 1 can survive. Keep event ticks separate from key ticks and simulation ticks.
4. Graph evaluation produces ordered child weights. Preserve stored child order, negative-weight clamping, near-zero fallback, mask-byte scaling and the distinct regular/displacement quaternion paths.
5. Procedural pose consumes published physical state and typed gameplay signals. Apply only proven operations; unresolved layer order is a named configuration choice.
6. Hierarchy propagation converts local to model pose. The documented native kernel expects parent-first order, normalizes composed quaternions and retains previous output for skipped LOD subtrees.
7. Rendering consumes model pose and a validated mesh palette. It never silently writes a visual correction back to body velocity.

The module boundaries above are our design. They are not recovered engine class names. [Executable math](../../reference/README.md) covers local kernels, not the full pipeline.

## Landing without inventing a selector

Known pieces include alignment weight, basis rotation, delayed tilt and translation shift. A positive start marker overrides the normal alignment envelope; the raw cross-product magnitude gate precedes normalization. Antiparallel vectors can therefore produce a no-op in the inspected local kernel. Preserve that behavior in the reference, even if an independent implementation offers a separately labeled robust fallback.

A decoded landing resource exists, but its name is not evidence for speed thresholds, selection, blend duration or crash eligibility. The inspected graph ownership path did not close that selection. Keep `LandingSelection` as an explicit unresolved adapter returning clip ID, phase, blend envelope and reason. A procedural fallback may be implemented, but label it as designed behavior.

Suggested integration flow:

```text
physical = published_body_state(tick)
landing = classify_landing(physical, contact_history)  # unresolved policy
selection = landing_selector(landing)                # configurable substitute
pose = sample_and_blend(selection, animation_clock)
pose = apply_documented_alignment(pose, supplied_alignment_inputs)
pose = apply_documented_tilt(pose, supplied_motion_inputs)
model_pose = propagate_hierarchy(pose)
```

The producer of each supplied alignment input still needs evidence. This order is an integration proposal, not a recovered complete call sequence. Do not turn visual absorption into a second physical impulse.

## Tricks and root motion

Store body orientation, entity target orientation and visual skeleton root separately. The inspected snowboard notification was a no-op; that does not prove every component ignores the target. The indexed physical-pose follower's angular caps are not established player trick limits. Log each representation and its timestamp to identify double application, axis flips or momentum resets.

The asset notes report no distinct root-motion section and no loop flag in the inspected clip records. Root translation channels and seam similarity do not establish gameplay displacement or runtime looping. Require a consumer before applying either to physics.

## Walking, feet and snow

Walking controller behavior remains a research gap. For an independent implementation, expose foot contact position/normal, material, support velocity and penetration limit as inputs. A designed foot-placement solver may use pelvis compensation and two-bone IK, but neither its order nor its tuning is recovered here. Snow-depth rasters do not prove original foot sinking. Track authored motion, procedural offset and final contact error separately.

## Acceptance scenes

Use invented assets first: an idle three-joint rig; a two-clip crossfade; an additive lean; a loop endpoint; a skipped LOD subtree; a landing on tilted ground; an airborne full rotation followed by contact. Check zero-input drift, quaternion norm, parent composition, event duplication, blend order, foot penetration and independence of body momentum from pose evaluation. Use supplied original clips only in a private integration suite.

Open joins remain authored resource UID to compiled source key, active landing selection, complete procedural layer order, original foot/board constraints, active rig selection, packed vertex/resource-view conversion and the full walking state machine. A visually convincing substitute does not close those questions.

## Skeletal findings that supersede broader uncertainty

The [skinning chapter](../systems/animations/skinning/CLIENT_GUIDE.txt) already establishes final palette production, joint-remap fallback, origin rebasing and four/eight-influence GPU position kernels. The remaining questions concern active rigs and packed input conversion, not the existence of a palette formula. The [IK solve chapter](../systems/animations/ik-solve/CLIENT_GUIDE.txt) establishes the graph callback bridge, a two-segment intermediate-target kernel and weighted bone writes. Complete equipment-specific scheduling and all full-body stages remain open.

The [pose assembly chapter](../systems/animations/pose-assembly/CLIENT_GUIDE.txt) also documents conditional root-motion removal. Absence of a separate root-motion section in an asset record does not mean the runtime has no root-motion handling. The body-displacement consumer remains unresolved.

The [latest binding check](research/animation.md) establishes that the compiled source key is copied unchanged into the provider lookup key. The authored-to-compiled conversion still needs a producer trace. See the [skeletal review](research/skeleton.md) for sorted hash lookup, duplicate handling and active addon rig questions.
