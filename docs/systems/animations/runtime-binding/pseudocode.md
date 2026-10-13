> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Compiled resource construction

The newly recovered behavior separates object identity registration from resource construction. The authored owned output contains a 128-bit GUID and a 64-bit resource UID. The compiled DataNode contains a 64-bit source field and an embedded handle. Their matching widths do not prove their ownership join.

```text
factory(identity, optional_storage):
    node = optional_storage or allocate_and_construct_data_node()
    register_nonzero_identity(node, identity)
    return node

register_nonzero_identity(node, identity):
    if identity.first_word == 0 and identity.second_word == 0:
        return
    object_registry.register(node, identity)

clone_compiled_data_node(source, optional_destination):
    destination = optional_destination or allocate_and_construct_data_node()
    if destination was newly allocated:
        register_nonzero_identity(destination, zero_identity)
    clone_base_node(source, destination)
    destination.playback_slot = source.playback_slot
    destination.secondary_slot = source.secondary_slot
    destination.displacement_slot = source.displacement_slot
    destination.duration_slot = source.duration_slot
    destination.flags = source.flags
    destination.resource_source_field = source.resource_source_field
    initialize_embedded_resource_handle(
        destination.requested_resource_handle,
        source.resource_source_field,
        0)
    return destination
```

The zero-identity registration call in the newly allocated clone returns without reaching the registry. The final handle initializer is the exact next binary edge. Its third argument is zero in this clone; its meaning is unknown.

For example, cloning a compiled node with source field `K` passes `K` to the destination handle initializer. That proves the argument value, but does not prove that the resulting provider key equals `K`. Likewise, the idle authored resource UID `377807682600` is not yet proved to become `K`. Those two missing assignments prevent a complete resource-binding formula.

The runtime descriptor describes one local member at the source-field location. Its member hash and type word remain opaque. Its class CRC differs from the authored Atom class CRC. A loader or conversion between these classes is still required.

```text
authored_output.resource_uid
    -> UNRESOLVED authored-to-compiled assignment
compiled_node.resource_source_field
    -> verified handle_initializer argument
embedded_handle.provider_key
    -> UNRESOLVED initializer assignment
provider-selected resource
```

This pass adds no landing blend or temporal formula. Resource binding must close before following a landing state edge to a selected clip.
