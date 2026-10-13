> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Entity publication and the selected snow notification

The submitted trick target becomes an entity transform. The exact snowboard component's notification does not turn that target into body angular velocity. Other components can still consume the target, so the whole player's visible or physical rotation is not resolved by this result.

## Recovered publication

The target is a 64-byte transform with four rows. The wrapper supplies two pointers to the same target and five low flag bits set.

```text
publish_target(entity, target):
    packet.primary = target
    packet.secondary = target
    packet.flags = 31
    entity.publish(packet)

base_entity_publish(entity, packet):
    acquire_recursive_entity_lock(entity)
    entity.pre_notification_marker = 0
    for component in entity.components:
        component.before_transform_change(packet)

    entity.transform = copy_four_rows(packet.primary)
    update_optional_parent_transform_record(entity, packet)

    update_entity_transform_cache(entity, entity.transform,
                                  entity.optional_secondary_transform,
                                  entity.mode == 2)
    entity.post_notification_marker = 1
    for component in entity.components:
        component.after_transform_change(packet)
    release_recursive_entity_lock(entity)

derived_entity_publish(entity, packet):
    base_entity_publish(entity, packet)
    forward_transformed_packets_to_eligible_children(entity, packet)
```

The names describe the observed operations. The cache's ultimate owner and the hierarchy's matrix-composition convention are not fully recovered here. Treat those calls as unresolved helpers, not portable formulas for a renderer or body solver.

## Selected snowboard component

```text
snow_before_transform_change(component, packet):
    return

snow_after_transform_change(component, packet):
    if not component.flags.bit26:
        return
    if component.suppression_byte != 0:
        return
    if not packet.flags.bit3:
        return

    target = packet.secondary
    if packet.flags.bit4:
        component.selected_target_callback_A(target)
    else:
        component.selected_target_callback_B(target)

    # Both callbacks return immediately for the exact PlayerSnowboard
    # table and the base Snowboard table recovered here.
```

For flags 31, bit3 and bit4 are both set. An enabled, unsuppressed component selects callback A, which returns immediately. If the component is disabled or suppressed, it returns earlier. Flags 8 select callback B, which also returns immediately for these two tables.

There is no timestep, quaternion difference, angular-rate calculation, inertia operation or body velocity setter in this selected notification path. The older prescribed-pose follower's `(target COM - current COM) / timestep` and relative-quaternion rate are separate logic and are not inserted into this pseudocode.

## Example

Suppose an entity starts with an identity transform and receives a target whose basis turns 90 degrees about one axis. The publication copies that target into the entity transform. Before-change callbacks run while the stored entity transform is still the old one. After-change callbacks run after the copy. The exact snowboard after-change callback returns without changing a body.

This example does not predict the physical body's final orientation, the rendered pose or the next simulation step. Those depend on other receivers and later updates that this trace has not joined.
