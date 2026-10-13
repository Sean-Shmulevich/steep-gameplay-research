> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Contact and landing investigation

The new result is an object-level join from environmental query descriptors to the per-cell fluid profile and its force consumer. It also separates a retained collision-mask summary from a current material selection. The timer and actor skip flag have distinct writers, so sample131 remains an observed timing exception with a concrete possible ordering, not a discarded sample.

## New joins

Static byte-verified setup appends descriptors whose destination is each cell's environmental plane. Query entry clears each destination profile and thickness, then the hit callback resolves a collision material's fluid resource and writes the decoded profile into that plane. The face-force consumer reads that exact profile. A valid nonzero profile after completion of the same query generation is evidence of a profile-bearing selected hit. It is not proof that all colliders touch that material, and accepted backend hits can have no fluid profile.

The selected geometry can hold different profiles per cell or face. A single dominant name cannot replace them. One update-local map accumulates clipped volume per profile. A separate map counts backend-mask keys. Its modal key, with ties resolved by map traversal order, becomes a retained summary only if nonzero. The summary remains unchanged when the current update offers no nonzero winner. Its recovered consumer tests the low two mask bits. Calling it a material pointer or current material would be wrong.

The callback writes the backend mask before its geometric acceptance branch. A rejected candidate can therefore leave a mask without a selected fluid profile. The actor's numeric query category is a third quantity. It can change even when the landing query returns false. None of these three representations should be renamed rock/snow/ice from their number alone.

## Recovered local logic

For ordinary finite inputs, the joined physical update is:

```text
clear query destination profiles and thickness values
for accepted environmental hit:
    profile = resolve_fluid_resource(hit.collision_material).decoded_profile
    plane = adjusted_plane(hit, wrapper, query_branch)
    plane.profile = profile

for eligible clipped cell:
    volume = clipped_submerged_volume(cell, plane)
    positive_volume_sum += max(volume, 0)
    profile_volume[plane.profile] += volume
    mask_count[plane.backend_mask] += 1

immersion = positive_volume_sum / total_hull_volume
if immersion > float32(.001):
    absence_elapsed = 0
    contact_elapsed = float32(contact_elapsed + update_elapsed)
else:
    immersion = 0
    contact_elapsed = 0
    absence_elapsed = float32(absence_elapsed + update_elapsed)

derive_contact_summary()
# This later routine can clear immersion if its volume-weighted term <= 0.
# It does not recompute the timers on that branch.

# A separate actor refresh:
new_skip = absence_elapsed >= float32(.04)
contact_transition = old_skip and not new_skip
cached_skip = new_skip
```

The maps reset on selected geometry update entry. The retained mask summary has a longer lifetime. Per-cell validity is reset before geometric evaluation and is checked by the summary and impulse consumers. Stable pointers alone do not establish the generation of these records.

Landing entry uses the current timer predicate directly, while motion copying uses the cached actor skip. The ordinary directional route is:

```text
direction = normalize(select_actor_or_runtime_contact_direction())
candidate = absence_elapsed < float32(.04)
            and dot4(stored_motion, direction) < 0
if candidate:
    success, query_direction, numeric_category = nearby_surface_query()
    if success:
        direction = query_direction
    actor_category = numeric_category

if candidate or an accepted alternate state route:
    angle_degrees = acos(clamp(dot3(target_up, direction), -1, 1)) * 180/pi
    normal_motion = abs(dot3(stored_motion, direction))
    response_scalar = selected_base + selected_scale * normal_motion
    apply further upright, grab and state gates
```

State routes and classifier branches are partial. The virtual base/scale selector is not mapped to a named sport, and the response scalar is not independently a complete crash classifier or an animation severity input.

## Sample131 audit

The raw receipt remains skip=1, absence_elapsed=0 and immersion=0.20210166. The three reads span about 0.1034ms within a 4.0174ms request. The contact timer equals the current update step, about 0.01005070 update-time units. Identity guards passed; reads were sequential and non-atomic.

The separate writers permit an actor refresh to cache skip=1 before a physics contact update resets the absence timer. A recorder can then see skip=1 with the new positive immersion and timer0. This is a concrete explanatory sequence, not a proven execution history. We have not recovered the scheduler order or a common update generation tying the receipts together. The record-copy skip writer is another surviving path. The later immersion-clearing writer does not directly explain this positive-immersion sample.

The next sample has a changed motion snapshot despite skip remaining1 at both endpoints. An intervening refresh/copy transition is possible at the 157ms sampling cadence. Neither endpoint proves a continuous freeze.

## Prior results retained

The profile selection, adjusted-plane equation, clipped-volume immersion, .001 and .04 thresholds, landing directional gate, normal-motion scalar and query-category freshness warning were already known in run36/pass16/pass17. This run newly binds descriptor destinations, per-cell profile consumption, mask provenance/retention, separate skip writers, and post-timer immersion clearing. Authored rock and ice fluid profiles remain confirmed. The main-body mass result is unchanged and outside this task.

For the ordinary query branch:

```text
adjusted_point = hit_point + query_direction *
                 (hit_normal.z * query_thickness / dot(hit_normal, query_direction))
plane_offset = -dot(hit_normal, adjusted_point)
special_effective_thickness = max(observed_gap, float32(.001)) *
                              query_thickness / layer_range
```

The special gap branch and alternate vertical query route remain separate from the ordinary equation. Query thickness, wrapper layer range and Lua thickness metadata are different inputs.

## Weather and remaining gaps

The inspected material profiles are authored collision resources. The weather/time-of-day assets select authoring tracks and sky resources. No inspected edge connects these tracks to profile replacement, grip coefficients or immersion. A dynamic weather effect on contact physics remains unproved.

Missing runtime links are the scheduler order between physics and actor refresh, a durable query generation/success record, safe live descriptor discovery with generation guard, and resource identity from live decoded profile to the named asset. The static descriptor shape is now known, but pointer equality plus a stable read cannot prove freshness against reuse. No live experiment, game launch or process attachment ran. Addresses, offsets and instruction receipts are in [PRIVATE_EVIDENCE.md](evidence.md), with byte-proof.json (`byte-proof.json`; source artifact, not distributed) and field-inventory.json (`field-inventory.json`; source artifact, not distributed).
