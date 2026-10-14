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
2. Follow the shared resource-entry lookup and conditional release called by the now-identified acquire wrapper. The named binding caller, dispatcher and supplied function are statically connected below. Initialization order and active-session installation remain unverified.
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
Its other callees were not exhaustively traced. At this stage the supplied function's origin was open; the follow-up below
identifies a concrete binding caller and supplied target. Registration invocation
order, replacement policy and active owner remain open.
The authored UID-to-compiled-key edge and active landing selection remain open
as well.

The follow-up inspected three pdata-linked constructor/teardown bodies and one
12-byte leaf setter. Direct RIP-relative references were instruction-aligned
against available exception ranges; this search does not cover arbitrary
computed aliases or all leaf references. See the
[trace recipe](../../systems/animations/runtime-binding/trace-recipe.md) for
build-specific evidence anchors and the next bounded search.

## Named binding caller and acquired-entry wrapper

A second bounded static pass follows the only additional instruction-aligned
reference found to the acquire-by-ID name. A binding routine supplies that name
and a concrete function to the registry dispatcher. The dispatcher computes a
32-bit name key through an unexpanded helper, performs an unsigned lower-bound
search in the registry tree, and invokes the matching entry with the supplied
function as its argument. A missing key silently skips invocation locally.

This closes the static binding route, subject to matching name-key calculation
and registry initialization. It does not prove that the binding routine ran in a
particular game session. The name-key helper itself was not expanded in this
four-function pass, so its hashing convention remains explicit.

```text
bind_animation_callbacks(owner):
    bind_by_name(owner, "AcquireAnimationResourceById", acquire_one)
    ... bind other callbacks ...

bind_by_name(owner, name, supplied_function):
    key = opaque_name_key(owner, name)  # returns 32 bits
    node = registry.root
    candidate = null
    while node != null:
        if unsigned(node.key) >= unsigned(key):
            candidate = node
            node = node.left
        else:
            node = node.right
    if candidate != null and candidate.key == key:
        installer = candidate.function
        installer(supplied_function)
```

The supplied acquire function requests an allocation with both size/alignment
arguments set to eight, using two unexpanded allocation helpers. If the returned
pointer is null it returns null. Otherwise it initializes the wrapper and returns
its address. The resource key survives allocation and is forwarded unchanged to
the shared entry helper; the helper also receives a fixed manager address and
zero as its third argument.

```text
acquire_one(resource_key):
    allocation_context = opaque_allocation_context(8, 8, allocation_global)
    wrapper = opaque_allocate(8, 8, allocation_context)
    if wrapper == null:
        return null
    return initialize_entry_wrapper(wrapper, resource_key)

initialize_entry_wrapper(wrapper, resource_key):
    wrapper.entry = fixed_initial_entry
    entry = opaque_lookup(resource_manager, resource_key, 0)
    atomic_increment_u32(entry.counter)
    old_entry = atomic_exchange_pointer(wrapper.entry, entry)
    old_count = atomic_fetch_add_u32(old_entry.counter, -1)
    if old_count == 1 and (old_entry.flags & 0x00ffffff) == 0:
        opaque_release(resource_manager, old_entry)
    old_count = atomic_fetch_add_u32(entry.counter, -1)
    if old_count == 1 and (entry.flags & 0x00ffffff) == 0:
        opaque_release(resource_manager, entry)
    return wrapper
```

Preserve both decrements and their order. The first applies to the exchanged-out
entry, and the second to the lookup result. Do not simplify them by assuming the
two pointers differ. Arithmetic operates on 32-bit counters; the flags test uses
only the low 24 bits. The wrapper initializer dereferences the lookup result
without a local null check. A sentinel or a non-null lookup contract is possible,
but requires inspecting the helper. The flags' meanings and the release helper's
actual destruction policy are unknown.

These instructions establish a returned wrapper and resource-entry reference
handling. They do **not** establish that the wrapper's first pointer directly
addresses the provider row array previously described. That adapter/dereference
join remains open, along with the entry lookup algorithm and authored UID
conversion. Resource readiness, fallback selection and asynchronous loading
must not be inferred from the acquire name.

Next pass: inspect the shared lookup, conditional release, and name-key helper,
then follow the acquired wrapper into the row resolver if the remaining function
budget allows it. Keep allocation helpers opaque unless allocation semantics
become necessary to distinguish a resource hit from failure.

## Shared entry lookup

The next four-function static pass establishes the outer acquire helper's
reference increment, zero-key sentinel branch, inner entry-selection algorithm,
and the release wrapper's shared synchronization boundary. It also establishes
that the name-key helper uses the same seed/byte-hash helpers and NUL-terminated
length convention as registration. The seed's lifetime and hash algorithm remain
unexpanded; equal seed and input bytes produce matching arguments to the hash.

```text
acquire_entry(manager, key, supplied_record):
    if key == 0 and supplied_record == null:
        atomic_increment_u32(shared_empty_entry.counter)
        return shared_empty_entry
    enter_manager_guard(manager.guard)
    entry = find_or_create_entry(manager, key, supplied_record)
    atomic_increment_u32(entry.counter)
    leave_manager_guard(manager.guard)
    return entry

find_or_create_entry(manager, key, supplied_record):
    record = supplied_record
    if record == null:
        record = opaque_record_lookup(key)
    entry = null
    if record != null:
        encoded = record.index_word & 0x7ffff
        if encoded != 0:
            index = encoded - 1
            block = index >> 14
            slot = index & 0x3fff
            entry = address(manager.blocks[block].base, slot * 24)
    if entry == null:
        if key == 0:
            key = opaque_key_from_record(record, 0, true, 0xbb96607d)
        if key != 0:
            map_slot = opaque_map_find(manager.key_map, key, 0)
            if map_slot != null:
                entry = map_slot.value
    if entry != null:
        if record != null and record != entry.record:
            if record == supplied_record or opaque_context_mode() == 3:
                opaque_bind_record(manager, entry, record)
        return entry

    if key == 0:
        key = uint32(atomic_fetch_add_u32(generated_key_counter, 1) + 1)
    block = first_block_whose_free_head_is_not_uint32_max()
    if block == null:
        block = opaque_append_block()
        opaque_initialize_block(block, 0x4000)
    entry = pop_block_free_entry_or_null(block)
    # When popped: record=null, key=key, counter=0, flags=0.
    # The previous counter word supplies the next free index.
    opaque_bind_record(manager, entry, record)
    if uint64(key + 0xffffffff10000000) > 0x7ffffff:
        opaque_publication_context_begin()
        opaque_map_insert(manager.key_map, key, 0).value = entry
        opaque_publication_context_end()
    return entry
```

This is control/data-flow pseudocode. Conditional diagnostic virtual calls at
entry/exit are omitted; their purpose and effects were not inspected. Guard
enter/leave targets likewise remain opaque rather than assigned a platform lock
type. The release wrapper enters the same manager guard, calls an unexpanded
inner release helper, then leaves it. Actual freeing, rechecking and deferred
cleanup remain unknown.

Block descriptors have stride 16 and entries stride 24. The record's cached
index is one-based in the low 19 bits; zero means no cached index. The shown
routine does not bounds-check a cached index against allocated blocks. A key-map
miss can create an entry, so acquisition alone is not proof that clip bytes are
loaded or usable. The new-entry map-publication exception is exactly the
inclusive unsigned key range `0xf0000000` through `0xf7ffffff`; its semantic
meaning is unknown. It does not suppress the earlier map lookup.

The outer helper increments the selected entry before returning it. This explains
why the wrapper initializer later drops a temporary reference after taking its
own. The zero-key sentinel is the same initial entry used by the wrapper, so old
and new pointers can be equal. Counts and low flag bits still determine each
release call separately. Nonzero-key allocation failure behavior remains an
unproved contract: the inner path can pass a null entry to an unexpanded binder,
and the outer helper dereferences its result without a local null guard.

Executable local arithmetic is in
[animation_resource_index.py](../../../engine/animation_resource_index.py).
Tests cover one-based block boundaries, ignored high index bits, the inclusive
64-bit key-range exception, and release gates. This module neither reads memory
nor loads resources. The actual record lookup, record binding, inner release,
wrapper-to-provider-row join and authored UID conversion remain open.

## Record binding, deferred work and guarded recycling

A further four-function pass closes the inner release predicate, record-binding
branches and deferred queue insertion. Record lookup rejects zero keys or a
cleared global enable byte. Otherwise it enters a global guard and tries three
sources in order: an opaque helper returning a slot whose `+8` is the record;
another opaque lookup; then the existing key-map helper. It leaves the guard and
returns the selected record or null. Source identities and loading policy remain
unknown.

Binding first compares old and requested record pointers. Equal pointers return
immediately. Detaching a different non-null old record clears its low-19-bit
cached index, clears the entry pointer and entry flag bit 31, then repeats the
old record's cached-index clear. Preserve the repeated operation; do not infer
that it proves safety against concurrent rebinding.

For a non-null requested record:

```text
bind_nonnull_record(manager, entry, record):
    opaque_prepare_record(entry.key, record)
    index = opaque_entry_index(manager, entry)
    atomic_replace_low19(record.index_word, (index + 1) & 0x7ffff)
    if opaque_context_mode() == 3 and global_mode != 1:
        if entry.record == null:
            entry.record = record
            atomic_clear_bit(entry.flags, 31)
        enqueue(manager, {key: entry.key, record: record, entry: entry})
    elif entry.record == null:
        entry.record = record
        atomic_set_bit(entry.flags, 31)
```

If an entry already has a different non-null record, this function does not
immediately overwrite it. The special context branch still queues the new
record; the other branch leaves the entry pointer unchanged after writing the
new record's index. The unexpanded prepare/index helpers may have effects that
must be understood before treating this as an independent mutation API.

The deferred queue stores triples in 24-byte slots. It grows capacity by 2048
through an unexpanded preserve-resize helper when full. After successful room
checking it writes a triple, increments count and advances write index using
signed remainder. Its separate atomic notification counter increments even when
growth leaves insufficient room and insertion is skipped. Valid storage and
positive capacity remain caller/allocator contracts; notification count alone
is not a count of successfully inserted triples. No mutex is acquired inside
this queue helper.

Inner release uses a stronger predicate than the caller's decrement gate:

```text
release_under_manager_guard(manager, entry):
    if entry.flags.bit26 or entry.flags.bit24:
        return
    if entry.counter != 0 or (entry.flags & 0x00ffffff) != 0:
        return
    record = entry.record
    key = entry.key
    if record != null:
        atomic_clear_low19(record.index_word)
        if record.index_word.bit28:
            opaque_record_release(key)
        entry.record = null
        atomic_clear_bit(entry.flags, 31)
    atomic_set_bit(entry.flags, 26)
    if key != 0:
        if key not in inclusive_range(0xf0000000, 0xf7ffffff):
            if not entry.flags.bit28:
                opaque_erase_key(manager.key_map, key)
        block = opaque_find_entry_block(manager, entry)
        entry.counter_word = block.free_head
        block.free_head = signed_index_of_entry_in_block(entry, stride=24)
```

This reuses the counter word as a free-list link and marks bit 26 before
recycling. It does not directly free the block's allocation. The meanings of
bits 24, 26, 28 and 31 are deliberately described by their operations rather
than named as loaded/ready/owned. Record bit 28 and entry bit 28 are distinct
fields. Lookup acquisition, record attachment, queued processing and readiness
remain separate stages.

Executable helpers now include the guarded release predicate and low-19-bit
index writer. Tests distinguish caller eligibility from the inner recheck and
cover index wrap/truncation without treating overflow indices as valid.

Next: find the deferred triple consumer and the producer of its context/mode
gates, then connect its processed record to the provider row reader. The authored
UID conversion and runtime clip/landing selection remain unresolved.

## Manager mode transition and loading-thread join

The next bounded pass establishes the manager mode setter and its processing
wrapper. This narrows the route into deferred processing; it does not yet decode
the triple consumer or prove rejection of stale queued records.

```text
set_manager_mode(manager, new_mode):
    old_mode = manager.mode
    manager.mode = new_mode
    if new_mode == 1 and old_mode == 0:
        wait_while_loading_pending_or_busy()
        process_manager(manager)
        wait_while_loading_pending_or_busy()
    return old_mode

process_manager(manager):
    temporary_destructions = local_collection()
    enter(manager.processing_guard)
    enter(loading_thread.destruction_ring_guard)
    enter(manager.entry_guard)
    opaque_process_phase(manager)
    process_resource_release_phase(manager, temporary_destructions)
    leave(loading_thread.destruction_ring_guard)
    leave(manager.processing_guard)
    leave(manager.entry_guard)
    if manager.mode == 1:  # re-read after leaving the guards
        for object in temporary_destructions:
            if object != null:
                allocation_context = opaque_allocation_context(object)
                object.virtual_destructor(0)
                opaque_free(object, allocation_context)
    release_temporary_collection_storage_if_owned()
```

The release phase is the same previously studied caller that publishes staged
loading-thread destructions. See [loading-thread lifecycle](../LOADING_THREAD_LIFECYCLE.md).
The mode is written **before** the first wait. Only the 0-to-1 transition performs
these waits and processing; other transitions simply store and return the old
value. The two waits poll pending destruction and busy fields, with a helper call
between retries. They neither inspect staged destruction nor exclude producers.
The processing wrapper releases its guards in the shown order, not reverse
acquisition order. Neither sequence is permission to replace native state.

Two additional local joins were inspected:

- Record preparation receives both key and record. Under a global guard it tests
  record flag bit 28 and conditionally calls the same opaque map operation twice,
  once with the record pointer and once with the key. The map operation and
  publication-context helpers remain unresolved; no erase/insert identity is
  assigned from this caller alone.
- Entry-index calculation scans block descriptors in order. It divides the signed
  pointer difference by 24 with truncation toward zero, then compares the low
  32-bit quotient unsigned against the block's count. The first accepted block
  returns `(block_index << 14) + quotient` in 32-bit arithmetic. No match returns
  `0xffffffff`, which the binder's index-plus-one/mask turns into zero. There is
  no explicit alignment test here; valid entry pointers remain a caller contract.

Next: inspect the opaque processing phase and its called triple consumer. Match
its key/record/entry accesses to queue storage and distinguish removal, binding,
and destruction work before introducing a reconstructed queue executor.

## Deferred triple consumer and current-record dispatch

The consumer holds the manager entry guard and atomically exchanges a separate
published count with zero. It executes that captured count's decrement-to-zero
loop, removing one 24-byte triple per iteration. The producer previously traced
increments a different counter. Their publication join remains open.

```text
consume_published_triples(manager):
    enter(manager.entry_guard)
    remaining = atomic_exchange_u32(manager.published_count, 0)
    while remaining != 0:
        # Native path requires a populated ring for each captured iteration.
        key, queued_record, entry = pop_ring_triple(manager)
        if entry.key == key:
            atomic_set_bit(entry.flags, 31)
            current_record = entry.record
            if current_record != null:
                dispatch_record(dispatch_registry, current_record)
        remaining = uint32(remaining - 1)
    leave(manager.entry_guard)
```

The queued record is copied out of the ring but is not consumed by this function.
The match compares the full key against the pointed-to entry's current key. It
does not compare record identity, allocation generation, entry counter, or the
recycled bit. Reuse with a different key is skipped; equal-key reuse is not
rejected locally. A broader lifetime/queue contract may prevent it, but remains
unproved. The flag CAS reloads flags on retry and preserves other bits.

If the captured count exceeds ring population, the inspected code reaches an
entry dereference with a null local pointer. This is a required count/population
invariant, not a claim that a live execution violates it. Producer growth failure
and the missing publication join must be understood before modeling this as a
safe general-purpose queue. The independent decision helper implements only the
key check, flag update and current-record dispatch choice; it does not execute
the native ring or invent a lifetime guard.

Dispatch takes a guard on its registry, obtains an entry from the current record
using the shared lookup with key zero and explicit record, and temporarily
increments that entry's counter. It uses the resulting entry key to find a
registry value, then drops the temporary reference and runs the known inner
release when required. A found registry value is processed before leaving the
registry guard. This establishes a route to registered per-resource work, not yet
the provider row resolver or clip readiness.

The registry-value processor's local gate is:

```text
entry = registry_value.entry
mask = thread_local_word | (all_64_bits_set if entry.flags.bit31 else 0)
if (raw_pointer_bits(entry.record) & mask) == 0:
    return
for index in current_item_range:
    if item_state[index] == 0:
        if opaque_prepare_item(registry_value, index, prepare_context):
            item_state[index] = 1
    if item_state[index] != 0:
        opaque_process_item(registry_value, index, process_context)
```

The raw pointer-bit test is preserved without assigning undocumented semantics to
the TLS word. With bit 31 set it reduces to a non-null record check. The item
count is a 16-bit field re-read as the loop proceeds. The two item helpers remain
unexpanded; state value one must not be labeled loaded, decoded or rendered yet.

A nearby loading-thread phase inspected as a candidate was a different mechanism:
it visits newly appended 16-byte callback records since a saved index, calls each
function, then updates that saved index under a guard. It does not consume this
triple ring. Keeping the two mechanisms separate avoids a false scheduler join.

Next: locate the producer-to-published-count transfer and inspect the two item
helpers to identify which work is performed. Then follow their result toward the
provider row reader. These remain static findings without a live readiness or
safe-modification claim.

## Item prerequisites and first-row versus all-row dispatch

Four more bounded bodies establish the item helpers' control flow and two guarded
branches. Both helpers repeat the entry record/TLS-derived pointer-mask gate,
then construct a temporary resolution object from the selected 24-byte item
descriptor. The resolver implementation and descriptor grammar remain opaque.
Its output contains 64-byte rows and a 16-bit count.

```text
prerequisites_pass(rows):
    if rows.count == 0:
        return false
    for row in rows:
        handle = row.optional_handle
        if handle != null and handle.target == null:
            return false
    return true

prepare_item(receiver, item_index, context):
    record = gated_current_record(receiver.entry)
    if record == null:
        return false
    temporary = opaque_resolve(record, receiver.items[item_index], 0, 0, 0, 0)
    success = false
    if prerequisites_pass(temporary.rows):
        output = opaque_context_slot(context, uint32(item_index + 1))
        row = temporary.rows[0]
        if opaque_handle_predicate(row.optional_handle):
            guarded_prepare(row.optional_handle.target, output)
        else:
            opaque_prepare_row(row, output, row.word32, true)
        success = true
    destroy_temporary(temporary)
    return success

process_item(receiver, item_index, context):
    record = gated_current_record(receiver.entry)
    if record == null:
        return false
    temporary = opaque_resolve(record, receiver.items[item_index], 0, 0, 0, 0)
    success = false
    if prerequisites_pass(temporary.rows):
        output = opaque_context_slot(context, uint32(item_index + 1))
        for row in temporary.rows:  # count re-read during iteration
            if opaque_handle_predicate(row.optional_handle):
                guarded_process(row.optional_handle.target, output)
            else:
                opaque_process_row(row, output, row.word32, true)
        success = true
    destroy_temporary(temporary)
    return success
```

A missing optional handle passes the prerequisite check. A present handle with a
null target fails. Do not collapse those two cases into a generic null-resource
failure. Preparation validates **all** rows before dispatching only the first;
processing validates all rows before iterating all rows. They obtain their output
slot using item index plus one, from distinct caller-provided contexts.

The return value becomes true after dispatch, without testing a dispatched
helper's return value. Thus the caller's item-state byte becoming one proves only
that this local preparation path passed its checks and dispatched work. It does
not by itself establish decoded data or successful animation playback. The
processing result is ignored by the previously inspected item loop. Temporary
resolution storage is cleaned up on normal paths after construction, including
prerequisite failure; exception behavior remains unverified.

Both guarded branches use the same global guard. Each fetches an opaque current
owner identifier, compares it to the stored owner, spins on a compare-exchange
lock word if different, and increments nesting depth. It calls a distinct opaque
prepare/process operation with the target and output pointer. On return it
decrements depth; at zero it resets owner to `0xffffffff`, executes a locked
operation as a barrier, and clears the lock word. The same-owner bypass and
depth counter establish local reentrancy; identifying the owner helper as a
specific platform thread-ID API is unnecessary and remains unproved here.

This is a resource-resolution dispatch protocol used on the traced animation
acquisition path. It is not yet an animation sampling algorithm. Highest-value
next targets are the temporary resolver and handle predicate, or the guarded
operations if those reveal a concrete resource type. The staged-to-published
count transfer remains a separate open synchronization edge.

## Resolver construction and caller-specific branch narrowing

A four-function follow-up resolves the handle predicate and traces constructor
arguments through resolution and row assembly. The predicate is exactly:

```text
has_backed_handle(handle_field_address):
    handle = load_pointer(handle_field_address)
    return handle != null and load_pointer(handle) != null
```

Both return branches were inspected. This predicate alone is not a type test or
animation-readiness test. More importantly, the traced item helpers pass zero for
the resolver's handle-construction mode. That zero reaches the row builder,
which initializes each row's optional handle to null and skips handle creation
when mode is zero. Thus, absent unproved side effects or concurrent mutation,
these callers reach the **direct row operations**, not the guarded optional-handle
operations described in the prior section. The guarded helpers remain accurate
local findings but are not established active work on this particular route.

```text
construct_resolution(output, record, descriptor, options):
    initialize_empty_inline_row_array(output)
    metadata = record.virtual_metadata()
    resolve_into_rows(descriptor, record, metadata, output, options)
    return output  # inner boolean result is not propagated here

resolve_into_rows(descriptor, record, metadata, output, options):
    scratch = initialize_1024_work_records()
    intermediate = inline_pointer_array()
    if not opaque_traverse(descriptor, record, metadata, intermediate,
                           scratch, options):
        success = false
    else:
        assemble_rows(output, intermediate, options)
        success = true
    release_owned_intermediate_storage()
    release_owned_scratch_storage_in_reverse_order()
    return success

assemble_rows(output, intermediate, options):
    reserve_output_for(intermediate.count)
    for source in intermediate:
        opaque_normalize(source)
        row = copy_selected_source_fields(source)
        row.optional_handle = null
        if options.handle_mode != 0:
            if source.special_byte != 0 or options.handle_mode == 2:
                row.optional_handle = opaque_acquire_handle(source, options)
                # Native path also manages two handle reference counters.
        append_row(output, row)
        options.output_pointer = source.auxiliary_pointer
```

The copy pseudocode abbreviates field layout only; the evidence recipe preserves
its mapping. Normalization and traversal are still opaque, so the source grammar
and authored-ID interpretation remain unresolved. General nonzero-mode handle
reference counting is not reduced to an invented ownership contract here.

The constructor sets row storage to an inline area, initializes an empty count
and a packed capacity/ownership word. Resolution uses 1024 scratch records of
144 bytes; their existence is not proof of a maximum authored graph size because
traversal behavior is uninspected. Row assembly creates 64-byte rows. The row
handle field is null in the mode-zero path before append. Normal return cleans
owned scratch storage; exception safety remains unproved.

This changes the next investigation: inspect the direct preparation and
processing operations, plus their normalization/traversal inputs if needed.
Do not keep following the guarded branch solely because it was present in the
generic helper. Producer-to-published counter transfer and authored UID conversion
remain independent open edges.

## Direct row operations dispatch on descriptor metadata

Four further bodies show that the direct operations are descriptor-driven
dispatchers. This is not yet clip-specific arithmetic. Both distinguish indexed
work using row flag bit 1 and an index unequal to `0xffffffff`; row flag bit 0
selects a variant that bypasses several descriptor-pointer paths.

The shared packed-type rule is exact:

```text
effective_type(packed_word):
    primary = (packed_word >> 48) & 0x3f
    if primary in {0x17, 0x18, 0x1d}:
        return (packed_word >> 55) & 0x3f
    return primary
```

No names are assigned to these type codes. Preparation consults descriptor+18
for a specialized operation, while processing consults descriptor+28. The indexed
paths additionally exclude primary types 0x18 and 0x1d from some specialized
branches; preserve those explicit exclusions rather than generalizing the type
rule into a universal dispatch policy.

A descriptor notification branch is locally decoded:

```text
notify_descriptor(row, stage):
    if row.variant_bit0:
        return
    descriptor = row.descriptor
    metadata = descriptor.word_at_16
    if (metadata & (1 << 17)) == 0:
        return
    attachment = row.object_base + (metadata >> 18)
    callback = attachment.callback_at_16
    if callback != null:
        receiver = attachment - (attachment.word_at_24 & 0x3fffffff)
        callback(receiver, descriptor.word_at_4, stage)
```

This pseudocode states the observed Windows register arguments, not a recovered
source signature. Preparation's non-indexed route uses stage zero before its
remaining operation. Processing uses stage one after its operation, including
the inspected non-indexed helper. These are operation stages, not animation
keyframe times. The code also leaves attachment word bit31 in EAX before the
indirect call; its ABI significance remains unresolved and is not silently
modeled as a fourth argument.

The specialized and fallback operations themselves remain unexpanded. The new
result narrows the next work to concrete descriptor operations and the origin of
the descriptor/type metadata; no clip decoding, pose update, or authored UID
conversion is claimed.

## Staged-to-published count transfer closed

A targeted writer search identifies the missing transfer in a larger resource
processing routine. The producer increments the staged count; the transfer
exchanges staged with zero and conditionally adds its captured value to published;
the consumer separately exchanges published with zero. These are three distinct
atomic boundaries, not one atomic transaction.

```text
publish_resource_triples(manager):
    captured = atomic_exchange_u32(manager.staged_count, 0)
    if captured != 0:
        atomic_fetch_add_u32(manager.published_count, captured)

consume_resource_triples(manager):
    captured = atomic_exchange_u32(manager.published_count, 0)
    # Existing decoded consumer executes captured decrement-to-zero iterations.
```

The transfer is bracketed by two calls to the same unexpanded processing helper
with distinct integer arguments. There is no worker wake operation in the
exchange/add sequence itself. Do not borrow the loading-destruction publisher's
notification behavior merely because its counter arithmetic looks similar.
Likewise, the resource consumer's nonzero/decrement loop differs from the
loading-destruction consumer's signed-positive gate.

A staged arrival after the exchange remains staged for a later publication. A
publication after consumer capture remains published for a later batch. During
the interval between staged capture and publication, both stored counters can be
zero while the captured count is held in a register. Neither zero observation
proves queue emptiness or safe teardown. Native arithmetic wraps at 32 bits;
count/ring consistency still depends on producer success and outer ownership.

The executable resource-count helpers preserve these boundaries and report
whether the conditional add executes, without inventing notification or running
unbounded loops. Tests cover interleaved arrivals, later publication and wrap.
The higher-level routine's complete workload and invocation cadence remain open;
this result closes the count transfer, not scheduling frequency or pause safety.

## Callback passes around publication

The helper on either side of resource-count publication walks callback groups.
It sets the high bit of the group's packed count word, uses the low 31 bits as
the group count, and publishes each current global group descriptor through a
caller-supplied pointer. Groups whose descriptor flags overlap the supplied mask
are skipped. Eligible nonempty groups execute 32-byte callback records in reverse
storage order.

```text
run_callback_groups(groups, current_group_out, exclusion_mask):
    groups.count_word |= 0x80000000
    index = 0
    while index < (groups.count_word & 0x7fffffff):
        descriptor = global_group_descriptors[index]
        current_group_out.value = descriptor
        if (descriptor.flags & exclusion_mask) == 0:
            records = groups[index]
            for record in reverse(records):
                if record.receiver != null:
                    record.primary(record.receiver, record.argument,
                                   current_group_out)
                    if record.secondary != null:
                        record.secondary(record.receiver, record.argument,
                                         current_group_out)
        index += 1
```

The routine re-reads the group count during iteration. It snapshots each group's
record traversal bounds before invoking that group's callbacks, but it loads
record contents as it visits them. This is not an immutable callback snapshot or
a proof that callbacks may safely mutate the storage. It sets the high count bit
without clearing it locally. Scratch bookkeeping allocation/cleanup is omitted
from the pseudocode; ownership and mutation rules remain open.

The resource publisher runs this helper with exclusion mask 2, transfers the
staged count into published, then runs it with mask 1. Therefore a descriptor
with flags zero participates in both passes; one with both low bits set is
excluded from both. Masks select groups, not individual callback records. The
caller's EDX values zero/one are not used as a callback stage argument in the
inspected helper; record.argument supplies EDX to callbacks instead.

The immediate direct caller constructs a stack-local processing context, copies
caller inputs into it, calls a preparation helper, executes the resource routine,
and calls context cleanup. This proves ordering within that wrapper. It does not
establish invocation frequency, main-loop identity or an animation-frame boundary.
The next caller layer is needed before describing this as per-frame work.

## Loading-request cadence connected

The outer caller is now joined to the established loading-thread loop. That loop
runs its incremental callback phase, destruction batch, then this request phase.
The request phase drains destruction work again before selecting each request.
This proves a request-driven route to publication; it does not establish a
once-per-gameplay-frame call.

Request selection removes pointer entries from a ring under the loading-thread
ring guard, skipping null entries. The first non-null pointer becomes the active
request. When the ring empties, selection releases the guard and calls an
unexpanded refill helper; it retries if count becomes nonzero. Queue priorities,
producer identity and refill ordering remain open.

```text
process_loading_requests(thread):
    opaque_phase_begin(thread.phase_object)
    while not thread.stop:
        process_destruction_batch(thread)
        select_next_request(thread)
        request = thread.active_request
        if request == null:
            opaque_phase_end(thread.phase_object)
            break
        if request.kind_word != 0:
            request.alternate_callback(request.user_pointer)
        elif request.guard_target != null and not request.guard_target.check():
            opaque_rejected_request(request)
        else:
            if request.result_handle.target == null:
                process_resource_wrapper(request.inputs, reprocess=false)
                status = 1
            elif request.reprocess_byte != 0:
                process_resource_wrapper(request.inputs, reprocess=true)
                status = 2
            else:
                if request.context != null:
                    opaque_existing_context_operation(request.context)
                status = 0
            # Re-read active request/result after the operation.
            if thread.active_request.result_handle.target != null:
                if thread.active_request.completion_callback != null:
                    invoke_completion(status, thread.active_request)
        enter(thread.ring_guard)
        finished = thread.active_request
        thread.active_request = null
        opaque_release_request(thread, finished)
        leave(thread.ring_guard)
        opaque_phase_end(thread.phase_object)
```

This pseudocode abstracts pointer wrappers and callback argument assembly, which
are recorded in the trace recipe. The numeric callback statuses 0/1/2 correspond
to the three local branches; they are not named success/failure enums. Result
presence is rechecked after processing, and no completion callback is made on
these branches if the result remains null. The alternate kind branch has its own
callback and does not pass through the wrapper or that result test.

Stop is checked before entering request work and again after finishing a request;
it is not checked inside the resource wrapper. The active pointer is cleared
before the request-release helper under the ring guard. This establishes local
ordering, not safe cancellation, producer exclusion or a global drain condition.
Phase begin/end helpers remain opaque and are not labeled OS locks/events.

The processing wrapper and its callback/publication passes are therefore part
of loading-request execution on this recovered route. Consumer cadence for the
published animation triples is still a separate question. A loading-thread
request completion must not be used as a physics substep or pose-evaluation
boundary.
