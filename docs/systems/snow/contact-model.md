> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Contact, flight and landing are separate observations

Correction: the immersion system is not exclusive to visually snowy surfaces. The decoded collision-material bindings include rock and ice fluid profiles as well as snow. A rock profile has authored volumicMass 5000, layer range .015 and query thickness .30. Snow profiles commonly use volumicMass 1000. These gameplay values do not by themselves establish five times the total force or real-world material density.

Resource selection:

```
profile = resolve_fluid_profile(hit.collision_material)
plane = construct_adjusted_contact_plane(hit, profile.wrapper)
immersion = sum(clipped_submerged_cell_volumes) / total_hull_volume
if immersion > float32(.001):
    contact_elapsed += update_elapsed
    immersion_absence_elapsed = 0
else:
    immersion = 0
    contact_elapsed = 0
    immersion_absence_elapsed += update_elapsed
skip_motion_snapshot = immersion_absence_elapsed >= float32(.04)
```

The names `air_elapsed` and `snow_contact` in historical samples describe inferred gameplay usage. The measured predicate is insufficient immersion, not an independent proof that no collision shape touches any surface. Neither visual rock nor zero immersion alone identifies a backend collision state.

The decoded landing path adds directional and query conditions. Simplified local relationships for finite, valid vectors:

```
contact_direction = normalize(activity_active ? runtime_direction : actor_direction)
candidate = immersion_absence_elapsed < float32(.04)
            and dot4(stored_motion, contact_direction) < 0
# Further state/alternate-route gates apply.
if candidate:
    query_success, replacement_direction, category = nearby_surface_query(...)
    if query_success:
        contact_direction = replacement_direction

alignment_angle_degrees = acos(clamp(dot3(target_up, contact_direction), -1, 1)) * 180/pi
normal_motion_magnitude = abs(dot3(stored_motion, contact_direction))
landing_response_scalar = selected_base + selected_scale * normal_motion_magnitude
```

This is a partial local transcription, not the full crash classifier. The source has state gates, alternate landing routes, an upright evaluator and grab-related failure. The sport mapping of one selector remains unresolved. The query's categories 21..23 are numeric filter values; do not rename them rock/snow/ice. It can modify the category output even when it returns false, so a category value alone is not a current successful hit receipt.

Sources inspected: snow/materials/CLIENT_GUIDE.txt and named_data.json; snow/CLIENT_GUIDE.txt; pass16 landing exports; pass17 query evidence. Fresh instruction exports in this directory were byte-verified. No claim is made that this run invokes every branch.
