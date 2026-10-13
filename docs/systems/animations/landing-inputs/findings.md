> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Animation investigation

This pass used static image bytes and local decoded assets only. It did not launch the game, attach a debugger, inject input, emulate the controller or change remote files. Addresses and object offsets are in private/PROVENANCE.md (`private/PROVENANCE.md`; source artifact, not distributed). The local audit is reproducible with `python3 private/audit.py`.

## New joins and measurements

1. The one decoded landing clip joins by resource ID to `Group00_Set01_male_LANDING_TO_FWD_MED_SPEED`, duration 1 second. It contains 174 tracks, 1,330 samples and 85 distinct binding hashes. Ordinary direct-mapping sampling writes 62 of the male rig's 72 bones. Its exact resource ID has **zero entries in the rider graph's owned-output catalog**. Other similarly named landing clips belong to that catalog, but substituting one would change identity. This closes payload identity and exposes a selection gap. It does not discover an original landing selector.
2. A direct-mapping offline pose audit sampled all 61 times on a 60 Hz interval including both endpoints. The largest model-position change from the initial pose was 0.963403 authored units; the largest model-quaternion change was 101.592201 degrees. Hips changed by up to 30.100834 degrees, LeftFoot 17.832207 degrees and RightFoot 17.828901 degrees. These are motion in the decoded authored pose, before actor orientation, blending and IK. A bind-seeded unmapped child can move through its animated parent. No metre conversion is asserted.
3. Case-insensitive corpus queries give 401 labels containing IDLE and 283 containing LANDING, across 5,838 metadata entries. The rider graph has 220 IDLE owned-output records and 477 LANDING owned-output records. Those are records, not unique resources, executable states or locally decoded poses. The metadata `export_status=ok` refers to companion export receipts; it does not supply tracks in this checkout.
4. `Group00_Set00_male_STAND_IDLE` has a concrete resource-ID join to eight authored AnimationData records, with eight owned-output GUIDs. The selected example's five input variants are 4, 4, 2, 4, 2. This is an actual serialized record, not the illustrative state map. Its incoming state path and the conversion of these variants to runtime descriptors remain unproved. No decoded idle pose is among the ten representative payloads.
5. Named graph input writers now join the prior generic animation bridge to an explicit absorption formula. `AbsorbBoost` copies a stored scalar from a typed gameplay component. `AbsorbDistance` uses that component's virtual controller scalar and two threshold values, as shown below. `LandingForce` copies that component's data through the bridge cache. `TimeToLand` reads a different object, the guarded graph owner, through its getter. These two owner paths must remain separate. The code adds no unit conversion on these four scalar paths. Their names do not establish physical units.
6. The playback path resolves optional resource replacement before binding its playback instance. It stores a selected resource, segment start/end times and duration/marker data in separate runtime tables. This joins previously exported routines into an inspectable object path. A catalog-owned resource is not sufficient to identify the backend resource actually sampled.

Full receipts, record offsets, GUIDs, payload hash, metadata inventories and every bone measurement are in private/asset-audit.json (`private/asset-audit.json`; source artifact, not distributed). private/image-receipts.json (`private/image-receipts.json`; source artifact, not distributed) verifies the image SHA-256 and all selected exported instruction bytes.

## Absorption reaching animation

The scalar producer has this finite-input policy:

```text
current = actor_controller.current_scalar()
limit = actor.special_limit
if limit == 0 or current > limit:
    limit = actor.default_limit
AbsorbDistance = max(current, limit) - current
AbsorbBoost = actor.stored_boost
```

The special limit remains selected at exact equality. For current 0.4, special limit 0.6 and default limit 0.8, distance is 0.2. For current 0.7, the special limit is exceeded and distance is 0.1. These are synthetic examples of the recovered rule. They are not observations of a rider. NaN comparisons and MAXSS operand behavior need separate handling if malformed values are permitted.

Two real authored scalar remap records consume AbsorbDistance. Both contain the same range:

```text
span = float32(0.6000000238418579 - 0)
fraction = clamp(float32(float32(1/span) * AbsorbDistance), 0, 1)
remapped = float32(float32(fraction * -1) + 1)
```

The values map roughly as 0→1, 0.3→0.5 and 0.6→0. A negative distance maps to 1 and a larger distance maps to 0. These are scalar graph outputs. Their outgoing bindings to a particular bone mask, landing blend or IK request have not been established. Calling this an absorption *blend weight* would cross that missing edge.

The physical rider scalar spring, its ten integration substeps and the two-stage physical target absorber were already known. This pass does not join this animation scalar to their final physical-height output. The virtual scalar getter's concrete implementation remains the next physical edge. The generic graph-to-biped-IK callback connection is already proved in `animations/ik-solve`; equipment-selected graph invocation and landing-specific activation remain open.

## Resource selection and pose application

The following is recovered runtime control flow for a node that has already been selected by a graph. It is not recovered landing severity-to-state arbitration:

```text
requested = data_node.resource_handle
selected = requested
for resource_provider in prioritized_provider_order:
    for replacement in resource_provider.rows:
        if replacement.key == requested.key:
            override_scalar = replacement.scalar
            replacement_flag = replacement.flag
            if replacement.has_resource:
                selected = replacement.resource_handle
                stop searching

resolve node flags from compiled integer/boolean inputs
bind node.playback_slot to selected
start_time = 0
end_time = selected.resource_length
if requested marker-bound inputs resolve:
    update start_time and/or end_time from those markers
if start_time > end_time:
    start_time = 0
    end_time = selected.resource_length

initialize duration_marker_slot from selected playback instance
if an accepted synchronization context yields normalized phase p:
    adjusted_phase = inclusive_wrap((duration*p - offset_seconds)/duration, 0, 1)
    emit marker context for adjusted_phase
```

A replacement row can match the resource key and write its scalar/flag without providing a resource. Search then continues. The first provider/row yielding a nonnull replacement wins; if all fail the original handle remains. Do not turn this into last-match selection. The scalar's use beyond its stored cache is not established here, so it is not called a playback rate.

Playback and pose use distinct numeric domains:

```text
phase_offset = offset_seconds / duration if abs(duration) > epsilon else 0
if abs(source_multiplier) <= epsilon: source_multiplier = 1
effective_root_duration = child_duration / source_multiplier

sample_start_seconds = resource_length * normalized_start_phase
sample_end_seconds = resource_length * (normalized_start_phase + phase_delta)
track_query_frame = truncate(float32(float32(sample_seconds) * 60))
```

The duration divisor can be negative. Phase wrapping preserves exactly 1. The phase delta becomes forward travel by repeatedly adding 1 only when it is negative. Actual per-update phase advancement dispatches through an installed backend callback. This pass identifies that precise callback edge but does not recover its elapsed-time/rate law.

The node's displacement-cache path uses absolute seconds as `resource_length*start_phase` and `resource_length*(start_phase+phase_delta)`. Its ordinary evaluation path can resynchronize the playback instance at the normalized start and then advance it by normalized phase delta. Frame `dt` is a separate field passed to ancillary evaluation. Bone sampling, ordinary bind seeding and additive conversion remain the prior pose-assembly rules.

## Landing blending, with the unresolved selector explicit

```text
landing_inputs = published LandingForce, TimeToLand, Mode,
                 Archetype, AnimationSet, AbsorbDistance and other graph fields
selected_state_and_children = UNRESOLVED authored graph traversal(landing_inputs)
transition_duration = explicit_override if valid
                      else max(variable_duration, 0) if variable_mode
                      else literal_duration

weights = [max(child_graph_weight, 0) for child in selected_children]
if sum(weights) < epsilon:
    weights[0] = 1        # other tiny values remain
else:
    weights /= sum(weights)

visit children in stored order, skipping weight <= epsilon
first active child supplies pose
for each later active child:
    accumulated_weight += child_weight
    blend_alpha = child_weight / accumulated_weight
    blend child into current pose using blend_alpha
effective_channel_weight = global_weight * channel_mask_byte / 255
```

The generic transition-duration and child-blend policies were already known. Neither proves a selected landing duration, a sport-specific mask, severity threshold or leg-compression schedule. The 0.6 AbsorbDistance remap cannot be silently substituted for a child weight. The one-second decoded landing duration cannot be silently substituted for transition duration.

## What remains open

There is no proven chain from contact/landing classifier output through an authored state edge to a specific runtime landing node, transition duration, blend mask and final procedural leg pose. The sibling contact investigation identified physical landing metrics, but this pass does not equate them with LandingForce or a severity enum. The animation controller's entity lookup is statically visible; its ownership from the run36 validated player pointer is not yet closed. Passive live discovery must wait for that owner edge or reject the capture.

This pass adds resource-ID joins, measurements, scalar producer joins and runtime ownership receipts. It does not claim a new implementation of previously known generic interpolation kernels.
