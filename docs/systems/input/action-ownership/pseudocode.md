> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Callback ownership and invocation

This pseudocode describes the newly joined ownership path. Names are descriptive. It does not assume the selected manager-vector function returns the same storage as ordinary motion ingestion.

```text
construct_manager(manager):
    initialize_manager_fields(manager)
    owner = allocate_callback_owner()
    if owner exists:
        construct_callback_owner(owner)
    bind_callbacks(manager)
    continue_manager_setup(manager)

construct_callback_owner(owner):
    owner.type = callback_owner_type
    global_action_callback_owner = owner
    initialize_owner_fields(owner)
    // Callable binding occurs later in construct_manager.

bind_callbacks(manager):
    owner = global_action_callback_owner
    owner.vector_callable.function = selected_manager_vector_getter
    owner.vector_callable.reserved = 0
    owner.vector_callable.tagged_receiver = capture_receiver(manager)
    owner.vector_callable.invoker = vector_invoker
    // The binary writes each pair of fields in a separate 16-byte store.

sample_global_vector(action_id):
    owner = global_action_callback_owner
    callable = owner.vector_callable
    receiver = clear_low_two_bits(callable.tagged_receiver)
    temporary = callable.invoker(callable, receiver, action_id)
    return copy_vector(temporary)

vector_invoker(callable, receiver, action_id):
    temporary = callable.function(receiver, temporary_output, action_id)
    return copy_vector(temporary)

selected_manager_vector_getter(manager, temporary_output, action_id):
    // Exact next trace. Its storage read, fallback and freshness are unproved.
```

The capture code mixes pointer and tag bits. Clearing the low two bits yields the constructing manager's address with those bits cleared. Treat that as the manager receiver only under the object's usual alignment precondition. The code does not capture the carrier's flags source.

For example, if manager M constructs owner O, the binder stores O's vector function and a captured M receiver. A later sampler loads O and invokes the vector function on M. This proves which manager receives the action ID. It does not prove whether the function reads a current device value, a previously stored action, a fallback or a versioned sample.

There is no new age formula. The local sequence is owner publication, remaining owner initialization, callback binding, then further manager setup. Neither that sequence nor a stable pointer pair supplies a source-sample generation. The state override and later cooker/publication paths still require their own eligibility and ordering checks.
