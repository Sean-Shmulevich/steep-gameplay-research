# Motion-batch membership: registration and gathered receivers are separate

This bounded static pass narrows the membership gate in the [scheduler input audit](SCHEDULER_INPUT_AUDIT.md). It does **not** establish that the selected player belongs to `Physic::PreBeforeSimulation`. It establishes that the source registration list and the gathered execution array cannot be treated as interchangeable observations: the source-to-array helper retains the destination when its source is empty. A separate reset or consumption lifecycle must explain that branch before claiming current membership.

No game was launched, attached to or modified. This document contains semantic pseudocode and evidence summaries, not executable addresses, raw exports or game payloads.

## Established owner chain

The prior audit joins the graph's world pointer, the candidate registration list, the destination pointer array and the installed generic motion callback. The gather routine passes the source list and destination array to a concrete copy helper with append disabled. The range executor subsequently invokes its cached callback on each receiver pointer without adjusting the pointer. The selected player method can reach action ingestion if that same player receiver is present and its actor/controller gates pass.

This yields three separate identities to establish:

1. The source-list owner is the same world as the scheduled graph.
2. A source entry or gathered entry is exactly the selected player's receiver, with the supported virtual method table, rather than a nearby component or embedded motion object.
3. The gathered array and its consumption belong to the world request under investigation.

A source-list pointer is not an input sample generation, a player membership token or a guarantee that a receiver remains alive until execution finishes.

## Directly inspected copy behavior

The complete source-copy helper reads the source count and copies pointer-sized entries while holding the source's synchronization pair. Its append-disabled call path is:

```text
copy_registered_receivers(source, destination):
    enter_source_synchronization(source)
    count = source.count

    if count != 0:
        prepare_destination(destination, count,
                            preserve_contents = false,
                            reuse_capacity = true)
        if count > 0:
            copy_bytes(destination.storage + destination.count * pointer_size,
                       source.storage,
                       count * pointer_size)
            destination.count += count

    leave_source_synchronization(source)
    return count
```

For valid nonnegative counts, nonempty input replaces the destination's active contents with the source's receiver pointers. There is no per-entry filtering, receiver adjustment, virtual dispatch or explicit per-entry reference acquisition in this helper. Generic allocation and copying do not establish a receiver-lifetime guarantee.

The destination preparation helper has two relevant branches:

```text
prepare_destination(destination, required_count, preserve_contents, reuse_capacity):
    if reuse_capacity and required_count <= destination.capacity:
        if not preserve_contents:
            destination.count = 0
        return

    new_storage = allocate_pointer_storage(required_count)
    if preserve_contents:
        copy_existing_active_entries(new_storage, destination)
    else:
        destination.count = 0
    release_old_storage(destination)
    destination.storage = new_storage
    destination.capacity = required_count
```

Allocation details and allocator failure handling are outside this abbreviated pseudocode. The important verified operation is clearing the active count when preservation is disabled, in both capacity-reuse and reallocation paths.

**Empty-source exception:** when the source count is zero, the caller never invokes destination preparation. It does not clear the destination count or buffer on that path. For example, given a destination containing receiver A and an empty source, this local helper leaves A and the old active count intact. That example describes this helper alone; it is not proof that the scheduler later runs A. A prior reset, worker consumption or other owner operation may already have cleared the destination.

Do not replace this behavior with unconditional `destination = list(source)` and call the result recovered. An independent implementation may choose unconditional replacement, but should label it as its policy.

## What synchronization does and does not close

The source synchronization encloses the count read, destination preparation and byte copy. That supports a stable copy only relative to writers that participate in the same synchronization protocol. This pass did not recover those writers. The critical section does not, by itself, prove:

- where the selected player's pointer is inserted or removed;
- whether registrations are unique, ordered or refcounted;
- the lifetime of a copied receiver after source synchronization ends;
- exclusion between destination rebuilding and workers consuming that destination;
- that an empty source produces an empty batch in the current request.

The callable cached by the range executor and the pointed-to receiver lifetimes remain distinct objects with distinct release requirements. The general drain/teardown question is covered by the scheduler audit and is not answered by this list-copy lock.

## Registration remains an exact unresolved gate

A bounded search of unwind-described code for direct formation of the candidate list field and adjacent count field found the known builder and several unrelated owners. Inspected false leads included repeated property-object initialization/copy routines, object-size constants in deletion paths, and a controller update with a different owner layout. Matching a field displacement does not identify a world registration method. The search did not prove that the chosen player is ever inserted in this list.

This is not an exhaustive no-writer result. Generic registration code may calculate a list address from an index/table, receive an already adjusted pointer, enter through virtual dispatch, or occur in code outside the scanned unwind ranges. There is no basis here to label the list obfuscated or to conclude that it contains changing generic object types.

The next static target is therefore **the producer of the exact list object passed to the copy helper**, not arbitrary code with the same displacement. A useful trace must connect:

```text
selected_player_or_its_registration_owner
    -> registration_method(world, receiver, list_selector)
    -> same_list_address_used_by_gather
    -> concrete_insert_or_remove(receiver)
    -> source_synchronization_and_lifetime_rules
```

None of these arrows may substitute an embedded motion pointer for the original receiver without an explicit conversion. After finding an insertion, follow its matching removal and identify whether array snapshots hold references or rely on a world/request lifetime barrier.

## Revised membership release gate

Before claiming this player's action ingestion precedes a particular world request, establish the prior dependency/callback conditions **and**:

- selected world/graph identity and the selected player receiver;
- registration insertion or direct observed membership with owner identity;
- destination reset/rebuild epoch, including the empty-source branch;
- the selected receiver in the actual claimed range, or equivalent static guaranteed inclusion;
- receiver lifetime and actor/controller eligibility through that invocation.

For a future read-only observation, capture source and destination identities/counts separately, with read spans and a request association. Do not treat the destination's changing remaining-work counter as a stable registration count. A mismatch may reflect copying or consumption, not necessarily corruption. Asynchronous observations alone cannot establish these as one atomic snapshot.

For the reconstructed engine, immutable per-request receiver lists and explicit registration handles would make this inspectable. Those are proposed interface choices, not newly recovered original guarantees.

## Evidence scope

The copy helper was decoded directly from the analyzed image through its return: 165 bytes, 52 instructions. Its span SHA-256 is `474b5a3adf35d8ddc37f3e38dfede0fd96936d689a74a771c6b3f833e68f9640`. The destination preparation helper's capacity-reuse and allocation branches were inspected separately, including the active-count resets and final storage/capacity stores. The known gather call site was checked against the retained export; its append argument is zero.

The analyzed image SHA-256 is `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. The operation is a fresh static inspection, not execution of those routines. The broader dependency topology, selected player virtual-method join and callback invocation rules remain the evidence consolidated in the [scheduler input audit](SCHEDULER_INPUT_AUDIT.md).
