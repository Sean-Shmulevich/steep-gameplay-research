# Animation reconstruction: one resource-binding edge closed

Evidence category: newly inspected native code, with existing authored-asset research used only as context. No game launch, attachment, memory write, Studio substitution or video fitting was performed. The new result does not establish complete runtime clip selection.

## Newly checked result

The compiled animation node's resource-source member is copied **unchanged** into its embedded handle's provider comparison key. The earlier runtime-binding guide left this assignment open. Inspection of the actual initializer closes that particular edge.

The initializer writes the key before selecting or comparing its provider object. If the handle already has a backing block whose provider pointer equals the requested provider, it returns without rebuilding that block. A key change therefore does not by itself require backing-block reconstruction in this function. Conversely, sharing a provider pointer does not mean two handles select the same resource: their comparison keys remain separate.

The optional third initializer argument is an explicit provider-object override at this local boundary. When it is null, the acquire-by-ID slot of a globally referenced callback table is invoked with the resource key to obtain the provider. The provider's full class and callback implementation remain unresolved; do not give that callback a more specific resource-manager name yet.

### Portable pseudocode

Names below describe our interpretation of local roles, not recovered source identifiers.

```text
initialize_resource_handle(handle, source_key, provider_override):
    handle.comparison_key = source_key
    provider = provider_override
    if provider == null:
        provider = provider_callbacks.acquire_by_id(source_key)

    if handle.backing != null and handle.backing.provider == provider:
        return

    handle.virtual_slot_0(handle)  # reset/release behavior not traced here
    block = allocate_backing_block()
    if block != null:
        block.provider = provider
        block.callback = fixed_callback
        block.extra_pointer = null
        block.counter = 1          # exact initial value; ownership semantics open
    handle.backing = block         # null on allocation failure

clone_compiled_node(source, destination):
    ... copy existing compiled-node fields ...
    destination.resource_source = source.resource_source
    initialize_resource_handle(destination.handle,
                               source.resource_source,
                               null)

resolve_provider_row(provider, handle):
    for row in provider.rows_in_stored_order:
        if row.key != handle.comparison_key:
            continue
        output.scalar = row.scalar
        output.flag = row.flag
        if row.availability_pointer != null:
            return row.embedded_resource
        # An equal-key row with null availability does not terminate search.
    return null
```

The row resolver pseudocode restates the existing verified resolver, newly reread for the join. Output scalar/flag writes occur before the availability check; a failed lookup can therefore still leave outputs written by an unavailable matching row. Preserve this detail in a faithful reference adapter; do not silently make failure transactional.

### Now-established relationship

```text
authored output resource UID
    -- STILL UNPROVED authored-to-compiled conversion -->
compiled node resource-source member K
    -- exact copy --> embedded handle comparison key K
    -- equality lookup --> provider row with key K
    -- availability check --> row's embedded resource
```

This substantially narrows the missing identity join, but it does not prove that K equals an authored resource UID. The known idle UID remains an excellent witness for a future conversion trace. A matching numerical width, record name or identity GUID is not sufficient evidence.

## Second construction path confirmed

The previously decompiled node serialization/finalization callback was independently checked against the local image. It checks a byte through its context pointer, invokes two preparation helpers when enabled, re-reads the context byte, and initializes the same embedded handle from the same source member with a null provider override when enabled. Re-reading matters: the first helper calls are not assumed to preserve that gate. The callback itself contains no assignment establishing the authored UID's origin.

## What this buys an independent engine

An implementation can separate immutable resource keys, provider selection and backing lifetime instead of conflating graph identity, clip identity and object address. A test harness can expose each of these independently and log failed provider matches, repeated-key rows, changes of provider and allocation failures. These are useful mod/probe boundaries in the reconstructed engine.

It does not make arbitrary original-process key writes safe. Callback initialization, provider lifetime, graph-instance caches and clip/skeleton compatibility must still be honored. Nor does constructing a replacement engine automatically install a mod API in the original executable.

Recommended synthetic tests: preserve a key exactly through clone; change key while provider remains equal; replace provider and verify reset precedes replacement; absent allocation; duplicate keys with unavailable first row; ensure output writes on a failed lookup match the local kernel.

## Landing and procedural layer gaps

No new landing selector or procedural ordering was established in this pass. The decoded landing clip remains different from proof that the active runtime graph selects it. Playback, blending, alignment, delayed tilt and hierarchy propagation can be implemented as local kernels, but their complete scheduling and producer relationships must remain explicit interfaces. A Studio-authored landing animation or a video-estimated blend time cannot fill these gaps as recovered evidence.

## Highest-value next probes

1. Find writes to the compiled resource-source member in the authored-to-runtime conversion path. Use the known owned idle record UID and its separate output GUID as a paired witness. Success requires both input record interpretation and the member assignment, not a broad generic copy routine.
2. Follow the caller that supplies a function to the now-identified `AcquireAnimationResourceById` installer, then inspect that function's key-to-provider lookup. The global holds a callback-table pointer, not the function itself. The installed target remains unresolved; static binding callers are the next lead.
3. Once the UID join closes, bind a known idle output to a graph instance and follow state/transition selection toward landing. Log chosen node, clip key, skeleton binding, phase, mask and transition reason before trying to infer final pose from screenshots.
4. Keep backend phase advance and procedural layer scheduling as separate work. Provider binding success does not establish clock units or ordering.


## Provider callback installation and ownership

A bounded static follow-up closes the callback-slot installation edge. The parent
constructor passes an embedded subobject to the callback-table constructor. That
constructor publishes the subobject globally and clears its acquire-by-ID slot.
It also registers a small setter under the exact name
`AcquireAnimationResourceById` in a separate name-keyed registry. The setter
loads the globally published table and stores its incoming function pointer into
the same slot later called by resource-handle initialization.

The registered function is therefore an **installer**, not the resource lookup
implementation. The name identifies the binding; it does not establish the
meaning of authored IDs or the implementation of the supplied function.

```text
construct_callback_table(table):
    global_provider_callbacks = table
    table.acquire_by_id = null
    ... initialize other slots ...
    separate_registry.register(name_key("AcquireAnimationResourceById"),
                               install_acquire_by_id)
    ... register other bindings ...

install_acquire_by_id(supplied_function):
    global_provider_callbacks.acquire_by_id = supplied_function

select_provider(source_key, override):
    if override != null:
        return override
    return global_provider_callbacks.acquire_by_id(source_key)
```

This pseudocode preserves local assignment/call order. Registry hashing and
insertion remain opaque here. Neither the setter nor the inspected lookup path
checks that the global table and callback are non-null. That requires an external
initialization/lifetime contract; it does not prove a game defect. The constructor
publishes the table before finishing its initialization. An inspected teardown
clears the global, but no callback drain or concurrent safety follows from that
clear alone.

The parent constructor has no direct nonzero assignment to this embedded slot.
Its other callees were not exhaustively traced. The supplied function's origin,
registration invocation order, replacement policy and active owner remain open.
The authored UID-to-compiled-key edge and active landing selection remain open
as well.

The follow-up inspected three pdata-linked constructor/teardown bodies and one
12-byte leaf setter. Direct RIP-relative references were instruction-aligned
against available exception ranges; this search does not cover arbitrary
computed aliases or all leaf references. See the
[trace recipe](../../systems/animations/runtime-binding/trace-recipe.md) for
build-specific evidence anchors and the next bounded search.
