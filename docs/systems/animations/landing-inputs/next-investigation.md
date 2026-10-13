> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Next step

The next action should be one bounded binary trace, before live sampling. A resource-owning idle record is now known, but its serialized output has not been proved to initialize a runtime data node's resource handle. The actor-to-animation-controller ownership path is also incomplete. A live search that guesses either would be unreliable.

## Chosen trace

Follow the metadata-aware clone/conversion producer into AnimationDataNode's requested-resource handle, using the standing-idle record already decoded in private evidence.

- Producer input is the first standing-idle owned-output record retained in private/asset-audit.json (`private/asset-audit.json`; source artifact, not distributed). It has a validated resource identity, owned-output GUID and record hash.
- Consumer is the runtime AnimationDataNode's embedded requested-resource handle, reached by its virtual resource getter during cached evaluation. Its factory invokes the metadata-aware clone routine.
- Inspect that clone routine and the DataNode metadata provider. Identify the member description or conversion that copies resource identity into the embedded handle. Then inspect only that conversion and its immediate producer. Exact addresses and record locations are in [private/NEXT_TRACE.md](trace-recipe.md). Keep serialized Atom binding variants separate from compiled runtime variants.
- Bound candidate inventory to24 descriptor/member references and export at most6 concrete functions, each no larger than24,000 pdata-linked bytes. Inspect original image instructions at each selected assignment. Stop if the source grammar requires an unavailable compressed/serialized decoder.
- Success requires a field-level proof of owned-output UID→runtime node embedded handle, plus whether the provider lookup key is that UID or another key. A generic clone or pointer-copy routine without the source record interpretation does not pass.
- Record graph-record ordering and source-port lowering separately if reached. Stop after this one resource-binding edge; it does not require complete state-machine reconstruction. An unresolved incoming state edge must remain unresolved even if the resource handle conversion succeeds.

This trace permits a meaningful future idle-resource observation. It also prevents treating the decoded landing payload as selected by the main rider graph merely because its label resembles other graph clips.

## Proposed idle observation after ownership is proved

This experiment is proposed, not executed. It requires a proven read-only pointer path from the run36 validated player actor through the owning entity to its animation controller and graph runtime instance. Private evidence currently gives the reverse controller→entity→typed actor-context path. The missing inverse edge must be resolved first.

Question: does a stationary rider retain one idle resource after provider replacement, and how do its phase, segment bounds and downstream pose change during idle playback?

Preconditions/reset: human selects a stationary, non-ragdoll rider, confirms equipment and stance, and leaves the camera and input unchanged. Confirm actor identity, main-body identity, finite pose and no pending state change. Read-only snapshots acquire before/after identities, local monotonic timestamp and each field's read timestamp. Restart the acquisition if identities change. Do not declare this deterministic reset.

Input action: none. Observe60 seconds, with10 Hz bounded sampling and600 maximum records. This spans several cycles of the16.666667-second standing-idle candidate if it is selected. Graph deferral means sample count is not animation update count.

Measured fields: selected resource key/UID after override, requested resource identity, slot indices, normalized playback phase and delta, segment start/end and resource duration in seconds, node offset in seconds, root effective duration, published graph scalars in their unresolved units, active child weights as dimensionless scalars, channel mask bytes when their ownership is proven, local hips/foot transforms in authored units and quaternion XYZW. Capture controller-current scalar and both absorption thresholds only if their source owner is validated. Do not label the override scalar as playback rate until the backend advance producer is proved.

Safe discovery: use only the validated actor/entity/component path and graph-owned array descriptors. Check mapped region boundaries, vtables/type metadata, owner identity, low29-bit counts and self-relative pointer flags. Cap arrays to observed type limits and fail on impossible indices. Never scan arbitrary memory for idle strings or invoke virtual methods in the game process. Missing ownership makes the experiment fail before capture.

Expected outcomes: changing phase with a stable selected resource and repeated pose values supports idle playback of that resource; a stable requested resource with changing selected resource shows provider replacement; stable resource with changing active child weights shows layering rather than clip replacement; phase stalls that coincide with graph deferral identify scheduler behavior requiring finer observations. None of these establishes a full state selector.

Failure conditions: actor replacement, nonfinite fields, array bounds failure, activity/input that moves the rider, unresolved selected-resource identity, missing weights/masks, or reads too far apart to compare one update. Retain read timestamps and flag races instead of inferring atomic transitions.

Remaining unproved: landing severity-to-resource selection, sport masks, landing interruption policy, root-motion feedback and landing IK scheduling. A later landing experiment should compare classifier output, selected resource, child weights, published AbsorbDistance and hips/feet across one human-controlled drop, after those ownership paths are independently validated. The idle experiment cannot prove them.
