# Action binding insertion and a concrete vector reset writer

This static pass closes a binding-list insertion path and a writer to the same action-vector field used by motion and snow. The writer **clears** the vector when a selected binding collection is refreshed. It does not yet explain how device input repopulates the vector or identify a committed sample generation.

No game was launched, attached to or given input. Existing gameplay-call exports supplied concrete entry points; the subsequent small callees were decoded directly from the analyzed image. Names below describe roles, not recovered class names. No Studio-created animation or video estimate is involved.

## Binding insertion now has a concrete path

A gameplay caller invokes a manager operation with a specific binding identifier. That operation visits four context slots in the inspected branch. For each context, it enters the manager's exclusive accounting and calls a context helper that:

1. Fetches a binding pointer from that context's indexed binding table using the supplied identifier.
2. Fetches the identifier's group/category index from a separate integer table.
3. Selects the corresponding group record in the same group area used by action lookup.
4. Reserves pointer-array capacity when necessary, increments the group's count and appends that binding pointer.

The append helper has no local duplicate-membership check. Caller preconditions matter: the inspected gameplay caller tests a related predicate before insertion, and neither the helper nor its four-context caller provides general bounds validation for arbitrary external arguments. This is not a safe native API for mod scripts.

```text
append_binding(context, binding_id):
    binding = context.binding_table[binding_id]
    group_id = context.binding_group_table[binding_id]
    group = context.binding_groups[group_id]
    reserve_pointer_capacity_if_needed(group)
    group.count += 1
    group.items[group.count - 1] = binding

manager_add_binding(binding_id):
    for context_slot in the_four_slots_used_by_this_caller:
        enter_manager_exclusive_accounting()
        context = manager.contexts[context_slot]
        append_binding(context, binding_id)
        if context.active_byte != 0:
            run_context_refresh_preamble(context)
            refresh_binding_groups(context)
        leave_manager_exclusive_accounting()
```

This inserts a **binding pointer into a context group**. It does not allocate an action or insert a new action-ID value into the tagged map. The binding's map and its action objects already exist when this path runs. Their original allocation and map-insertion path remain open.

The companion removal route searches the selected group for a binding with the matching identifier and invokes an array-removal helper. It then takes the same active-context refresh path. Thus the newly identified reset is associated with binding changes on these concrete routes; it must not be described as an unconditional once-per-frame input update.

## The reset reaches the sampled vector

Action lookup and the refresh path share a concrete ownership chain:

```text
manager -> context -> group -> binding -> binding map -> stored action pointer
```

Lookup reads the map root from the binding-map object, asks the existing tagged-map lookup for an action-ID value slot, and dereferences that slot to obtain the action object. Its returned payload and vector accessor together read the action's sampled vector.

Refresh passes that same binding-map object to a helper that reads the same map root and enumerates value slots. Its first-entry helper first calls the **same key lookup routine** with key zero; if no slot exists, it calls the next-entry routine. The loop dereferences the returned value slot before performing these writes:

```text
reset_binding_actions(binding_map):
    cursor = zero_initialized_cursor()
    slot = first_action_slot(binding_map.root, cursor)
    while slot exists:
        action = *slot
        retained_byte = action.status_byte
        action.sampled_vector = four_zero_lanes
        action.adjacent_vector = four_zero_lanes
        action.adjacent_scalar_storage = zero_dword
        action.status_byte = retained_byte
        if action.optional_owner == null or
           action.optional_owner.callback_suppression_byte == 0:
            action.virtual_reset_or_refresh_callback()
        slot = next_action_slot(binding_map.root, cursor)
```

`sampled_vector` is the exact action-relative field established in [input probes](research/input-probes.md), not a similarly positioned field on the manager or carrier. The adjacent vector and scalar storage have not been assigned device, filtered-input or timing semantics. The retained status byte is written back unchanged in this local slice.

The same map-root receiver and value-slot dereference establish ownership of this write. The first-entry helper's direct use of the existing lookup supplies an additional concrete join. The larger next-entry routine has multiple tagged-container cases; this pass does not claim to have independently reconstructed every case or proved exhaustive enumeration for malformed containers.

## Gates and ordering that matter

The active-context refresh walks three groups in stored order, and each group in reverse binding order. It resets a binding's mapped actions, then checks that binding's blocker. A nonnull blocker with a nonzero control byte stops **that group's inner walk**; the refresh continues with the next group.

This differs from the previously inspected action lookup, where encountering the corresponding blocker after a failed lookup ends the overall search. Reusing one generic traversal routine for both operations would lose that distinction.

The action callback follows the vector clearing and is skipped only by its optional-owner suppression gate. Its actual concrete implementation remains unresolved. It might initialize additional state, notify another owner or repopulate values; none of those interpretations is established simply by its position after the stores. The virtual target must be resolved from a constructor-supported action type, not from the manager's table.

The binding mutation and refresh are inside the manager's exclusive accounting in these callers. That closes a writer-side ownership fact for this route. It does not make the earlier vector getter atomic: the getter returns from manager read accounting before the caller copies the vector. Other lifetime or synchronization guarantees may exist and still require their own evidence.

## Implication for scheduler reconstruction

A vector becoming zero may represent binding reconfiguration and action reset, not a zero device sample or an absence of input ingestion. A telemetry recorder should distinguish context selection, binding membership and vector contents. An unchanged action pointer can survive a meaningful reset.

This path supplies no timestamp, input sequence or commit generation. The accounting recursion depth and reader/writer bits remain synchronization state. Counting the zero writes would count reset activity on this path, not accepted device samples.

The next concrete target is the per-action virtual callback reached immediately after clearing, followed by the action object's construction and map insertion. The callback is selected through the action object's third virtual table slot in this analyzed build. That is a research anchor, not a portable hook offset. Its receiver is the dereferenced map value. Resolving that receiver's actual type is the limiting step; no extra input-manager callback-owner search is necessary.

A secondary inspected path changes the manager's selected context under exclusive accounting: it clears the old context's active byte, stores the new selector and sets the new context's active byte. It does not itself write the sampled action vector. The selector can therefore change without providing a new vector generation.

## Evidence scope

The exact manager constructor, callback binding and vector getter ownership were established in [the input audit](SCHEDULER_INPUT_AUDIT.md). This follow-up used the existing gameplay call site to identify binding-add/remove operations, then inspected the concrete context append, binding-map reset and first-entry helpers. The action-vector stores and callback gate are direct instructions, not inferred from decompiler variable names.

The analyzed image SHA-256 remains `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. The four central functions inspected here comprise 438 bytes for removal/refresh, 336 bytes for addition/refresh, 181 bytes for pointer append and 171 bytes for action reset. These are bounded static observations; there is no new runtime validation, complete input-device pipeline, action allocator or native replay guarantee.
