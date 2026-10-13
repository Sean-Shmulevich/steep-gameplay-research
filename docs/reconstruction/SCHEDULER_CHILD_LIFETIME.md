# Physics-world child ownership and lifecycle

The two objects destroyed before the scheduler manager are optional polymorphic children of `PhysicsWorldComponent`. This pass closes their local initialization, cloning and pre-destruction callback paths. Their concrete runtime subclasses remain unresolved, so neither child can yet be classified as a submission gate, cancellation object or ordinary resource cleanup.

The component name comes from the inspected type descriptor, rechecked against the image. It is not inferred from field offsets. The component's constructor, clone and lifecycle callbacks were matched through its installed virtual table.

## Construction does not select either child type

The component constructor initializes both child slots to null. The world initializer that constructs the manager and scheduler does not assign a concrete object into either child slot. Consequently, inspecting the scheduler constructor alone cannot establish either child's virtual destructor.

This corrects an overly strong reading of the previous [teardown follow-up](SCHEDULER_SUBMISSION_FOLLOWUP.md): the children are destroyed first **when present**. They are not proven universally present barriers. A newly constructed component has neither child.

## Concrete clone and replacement behavior

The component's virtual clone copies each optional child through a common owned-object replacement helper. It passes the same caller-supplied clone flags to both child clones. The helper does the following:

```text
replace_with_clone(destination_slot, source_child, clone_flags):
    old = destination_slot.value
    if old != null:
        old.virtual_lifecycle_callback()

    # Reload the slot after callback; callback may have changed it.
    old = destination_slot.value
    if old != null:
        allocation_metadata = lookup_allocation(old)
        old.virtual_destroy(argument=0)
        free_allocation(old, allocation_metadata)

    if source_child != null:
        destination_slot.value = source_child.virtual_clone(
            optional_destination=null,
            flags=clone_flags)
    else:
        destination_slot.value = null

clone_physics_world_component(source, destination, clone_flags):
    clone_base_component_and_scalar_fields(source, destination, clone_flags)
    replace_with_clone(destination.child_a, source.child_a, clone_flags)
    replace_with_clone(destination.child_b, source.child_b, clone_flags)
    copy_other_component_reference_fields()
```

The source child's dynamic virtual clone selects the resulting concrete object. No fixed child factory is called at either slot in this path. The helper explicitly frees the old object after virtual destruction; the virtual call receives a zero argument, whose full mode semantics were not traced. The subsequent explicit free is the established allocation-release step.

The source pointer is captured before cleanup. This helper supplies no explicit self-replacement guard. Its intended calling contract must ensure the source is still valid after destination cleanup; cloning a component into newly allocated storage satisfies that ordinary use, but arbitrary in-place replacement is not established safe.

## A separate lifecycle callback reaches both children

The component's earlier lifecycle method performs this local sequence:

```text
component_lifecycle(component):
    conditionally_release_items_in_component_collection()
    component.collection_count = 0
    release_component_reference_handle()
    component.reference_handle = shared_empty_handle

    if component.child_a != null:
        component.child_a.virtual_lifecycle_callback()
    if component.child_b != null:
        component.child_b.virtual_lifecycle_callback()

    invoke_base_component_lifecycle(component)
    remove_embedded_callback_binding()
    invoke_embedded_callback_owner_lifecycle()
```

The same child virtual slot is called by the replacement helper before destroying an old object. This establishes a distinct pre-destruction lifecycle hook; it does not establish the semantic name `cancel`, `unregister` or `wait`. Calling that slot a completed drain would require inspection of its actual selected implementation.

The component destructor separately invokes each present child's virtual destructor, frees it and clears its slot before destroying the manager. The lifecycle method and destructor are separate entry points. Their universal calling order is not proved by observing their virtual-table placement.

## An adjacent lock is scoped to a different operation

A checked component callback optionally calls a no-op helper on the first child and then enters a component-owned record-maintenance routine. That routine obtains a packed writer reservation, waits for reader counts to reach zero, visits ten arrays of records, removes or updates records and releases its reservation. Its observed critical section contains record maintenance; this pass found no joined scheduler submission or manager teardown in it.

Therefore, the presence of this reader/writer protocol on the same component is not sufficient to call it the missing scheduler exclusion gate. The submitting and destroying paths must demonstrably share it before that conclusion is justified.

## Remaining concrete edge

The missing edge is now the source of the optional child instances: a factory, deserialization assignment or replacement writer that supplies a specific type. Once that source is found, inspect the installed child's clone, lifecycle and destructor entries, then test whether its lifecycle hook excludes new scheduler work or merely releases resources.

A bounded read-only runtime inspection could also identify the two child virtual tables for one active component, but no live inspection occurred here. Such an observation would establish selected types only for that instance and generation, not universal type selection or the safety of invoking the callbacks externally.

## Verification receipt

All work used the same frozen image identified in the [lifetime audit](SCHEDULER_LIFETIME_AUDIT.md). Function bodies were inspected within exception-table bounds, with chained fragments retained where present. No executable or asset payload is included.

| Checked role | Bytes | SHA-256 |
| --- | ---: | --- |
| Component constructor | 393 | `e92f37c35572d2702479d6844857354ac73a0505439e3063774af451c367aa0f` |
| Component clone | 214 | `39ceb8818ba3271257e5a4b0f1b48b7a2193665254631f416fb3ff5ab9ff79fe` |
| Owned child replacement helper | 179 | `1558fd00adf4b8211e879835e20371e1d3951250d348d4ec1abc1780822931e7` |
| Component lifecycle callback | 179 | `e3f4709d1c2848bf56066ddea84d42f1422146830ae7adcde29350315a3a19de` |
| Adjacent record-maintenance wrapper | 36 | `462828daa91f1aa7c420893e0abf20cbe07bebee833585ff8895bb8a9a02225f` |
| Record-maintenance routine | 462 | `303d66d6186023aecb9ced0daf1f99965952da9642c50d5df5eda90f7d8d8512` |

These findings narrow the ownership problem but do not resolve concrete child subclasses, prove a scheduler submission barrier or authorize invoking teardown routines as a pause mechanism.
