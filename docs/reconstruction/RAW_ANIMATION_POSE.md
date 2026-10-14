# Raw clip channels to explicit rig poses

`engine.raw_animation_pose.RawClipPose` joins a caller-supplied typed clip body to
a caller-selected decoded rig. It samples compressed channel buffers directly,
without converting them into a second set of decoded keyframes.

```python
from engine.raw_animation_pose import RawClipPose

adapter = RawClipPose(body_bytes, decoded_rig, unit_scale=1.0)
pose = adapter.sample(time=0.5, hint=30)
next_pose = adapter.sample(time=0.6, hint=36, cursors=pose['cursors'])
# local_pose and model_pose retain rig bone order.
# auxiliary values are separate from bone transforms.
```

The rig schema is the existing decoded pose-assembly export: each bone supplies
name, binding_hash, parent_index and local_bind translation/quaternion_xyzw.
Scale must be explicit and positive. This API assumes identity orientation
mapping; it does not choose a sport, graph, rig, addon, loop policy or root-motion
owner. Callers supply already-chosen float time and integer hint separately.
The current adapter requires a positive-duration clip and a nonempty valid rig.
Zero-duration placeholder records remain parseable but are not pose resources.

## Composition contract

1. Structurally parse the clip; reject unresolved shared references.
2. Adapt each supported serialized channel into its recovered runtime layout.
3. Map transform-track binding identifiers to the explicit rig's identifiers.
4. Seed local transforms with the rig's local bind pose, applying explicit scale
   to translations. Preserve absent components.
5. Sample every channel through registered decoding. Overwrite a matched
   translation or quaternion component; report auxiliary/unmatched tracks.
6. Propagate locals through the existing normalized hierarchy composition kernel.

This is an independent adapter built from [container framing](ANIMATION_CONTAINER.md),
registered channel sampling and the existing ordinary pose-assembly contract.
See [asset integration](ASSET_PIPELINE.md) for binding provenance and distinctions
between decoded assets, recovered code and authored substitutes. The adapter uses
existing rig validation and `reference.skeleton.native_compose` via the animation
module's hierarchy walker. It does not claim original object layout or scheduling.

Quaternion formats map to rotation; float3 vector formats 27/28/29 map to
translation. Scalars and opaque values are auxiliary even when their identifier
also matches a bone. Unknown transform identifiers do not create bones. Repeated
tracks targeting the same bone component or duplicate rig identifiers are rejected
pending explicit override/addon policy, rather than silently selecting one.

Local sampled quaternion values retain decoder rounding. Model hierarchy
composition normalizes rotations as documented by that kernel. Unit scale is
applied consistently to bind and sampled translations; it is not inferred from
names or automatically equated with metres. Physical player position is untouched.

## State, diagnostics and limitations

The adapter stores runtime channel bytes privately in caller memory. Each sample
creates local SampleState values and returns a new cursor list; caller state and
input rig data are not changed. A failed sample does not partially publish cursors.
The returned auxiliary values and poses are private caller data, not public-report
material. Public receipts contain only hashes, counts and aggregate errors.

Diagnostics identify unbound transform track indices, auxiliary indices and the
number of bound components. The adapter does not execute event bodies, infer
root motion, merge rigs, apply orientation variants, additive layers, IK or
procedural landing adjustments. Integration with the simulation's animation graph
and its checkpoint/replay state is still pending. The older decoded-key adapter
remains available and is not silently switched to a different sampling policy.

## Validation

Four synthetic tests cover component binding, bind fallback, hierarchy/scaling,
rewind/fresh cursor equality, auxiliary isolation, unmatched tracks, duplicates,
unresolved references and failure-state preservation.

The [private comparison receipt](raw_animation_pose_validation.json) covers six
original raw clip bodies, both explicit base rigs and five sample times, including
rewind: 60 poses and 4,320 bones. Both rigs are deliberately tested; this does not
prove which rig gameplay selects. Scale is explicitly 1 in authored units.
Against the prior independent pose-assembly reference:

| Quantity | Maximum absolute error |
| --- | ---: |
| Local translation component | 9.998e-8 |
| Local quaternion component, sign-invariant | 1.155e-7 |
| Model translation component | 2.488e-7 |
| Model quaternion component, sign-invariant | 1.419e-7 |

These selected comparisons are close, but they are not native pose observations
or bit equality. Hardware reciprocal-square-root seeds remain substituted, and
previously documented threshold disagreements at other samples remain valid.
