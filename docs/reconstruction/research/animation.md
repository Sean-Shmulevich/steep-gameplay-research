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

## Consumer callers and loading-request waits

The consumer has multiple direct call sites, including explicit request waits and
the already decoded manager-processing wrapper. The scan therefore does not
support a single universal consumer cadence. Two wait callers and their request
predicate/refill helper were inspected in this bounded pass.

One wrapper first calls an unexpanded submission helper, then repeatedly checks
for a matching request using staging lane 1. While the predicate is true it calls
an opaque wait helper on the loading thread's phase object. When the predicate
becomes false, it tail-calls the global triple consumer.

```text
matching_request_present(thread, key, lane):
    enter(thread.ring_guard)
    if thread.active != null and thread.active.key == key:
        result = true
    else:
        result = any(nonnull request with matching key and kind == 0
                     in thread.ready_ring)
        if not result:
            result = any(nonnull request with matching key and kind == 0
                         in thread.staging[lane])
    leave(thread.ring_guard)
    return result
```

The active-request check does not require kind zero; queued checks do. Null slots
are ignored. It inspects only the selected staging lane, not all lanes. The
literal lane passed by this wait wrapper is one. Valid signed ring geometry and
lane bounds remain caller contracts.

The other wait wrapper scans active request, ready-ring non-null entries, and
all four staging rings under the guard. If any is present it leaves the guard,
waits, and retries. If none is present it leaves the guard and tail-calls the
triple consumer. This is stronger than a single-key absence check but still does
not exclude producers or include all loading destruction/publication state.
Neither predicate can be exposed as global engine quiescence.

## Four staging queues and refill boundary

The refill helper makes an unexpanded virtual call before entering the ring
guard, then scans staging lanes 0 through 3 in order. It repeatedly pops from the
current lane, skipping null entries. When lane 1 is empty it temporarily releases
the guard, calls a special refill helper, reacquires the guard and uses that
helper's boolean to decide whether to retry the lane.

For each non-null request it decrements a separate queued count and appends to
the ready ring only if capacity exceeds count. No growth is attempted in this
local append path. It then either continues scanning or prepares a new context:

```text
if request.kind == 0 and
   (request.reprocess_byte != 0 or request.result_handle.target == null):
    request.context = allocate_and_initialize_context(request)
    opaque_submit_context(request.context)
    return_from_refill()
# Otherwise continue draining/scanning staging lanes.
```

The context is 112 bytes, retains an optional request-owned reference, initializes
three embedded objects, installs inline storage and copies the reprocess byte.
Allocation failure can pass a null context to the unexpanded submit helper; its
contract remains unknown. Ready-ring capacity exhaustion does not locally stop
subsequent context preparation or restore the popped request. That establishes a
required capacity/ownership invariant, not an observed game failure.

This narrows request ordering but does not name the lanes' semantic priorities,
prove fairness or establish where producers acquire exclusion. The next useful
ownership targets are the submission helper, special lane-1 refill and context
submit operation. Other consumer caller families remain unclassified until their
bodies are inspected.

## Request allocation, lane submission and worker notification

The request producer obtains a request pointer from a free-object ring under the
loading-thread ring guard. If its signed count is not positive, it leaves the
guard, calls the phase wait helper and retries. On success it pops a pointer,
decrements a separate free-object count and leaves the guard before calling the
request initializer. No stop check occurs in this local wait loop. Initializer
semantics remain open; a non-null free-ring entry is a required invariant.

Submission reads the signed lane and kind from the initialized request before
entering the guard:

```text
submit_request(thread, request):
    lane = signed32(request.lane)
    kind = request.kind
    enter(thread.ring_guard)
    thread.queued_count = uint32(thread.queued_count + 1)
    ring = thread.staging[lane]
    if ring.capacity > ring.count:  # signed comparison
        ring[ring.write] = request
        ring.count += 1
        ring.write = signed_remainder(ring.write + 1, ring.capacity)
    if kind == 0:
        thread.kind_zero_count = uint32(thread.kind_zero_count + 1)
    leave(thread.ring_guard)
    repeat:
        old = thread.notification
        desired = 1 if signed32(old) >= 1 else uint32(old + 1)
    until compare_exchange(thread.notification, old, desired)
    if signed32(old) < 0:
        opaque_notify(thread.event)
```

The notification uses the successfully replaced old value. Counter increments
and notification can occur even if the staging ring lacks room; there is no local
growth, bounds check for lane, rollback or insertion-success return. Preserve
those capacity/valid-lane requirements rather than claiming a lossless native
submission API. This closes the producer-to-worker notification relationship for
this path, not the opaque event's platform behavior.

## Lane-1 refill is a provider callback pass

The special refill helper saves the current TLS mask word and context mode,
clears the mask and sets mode zero. Under a distinct provider-list guard it
builds temporary records containing provider pointer, callback result byte and
callback-written metadata. A virtual provider query initializes each record's
metadata from a fixed default. It then leaves the guard and passes the temporary
records through an unexpanded ordering/selection helper.

After reacquiring the guard, it processes the selected records until an
ineligible record or exhaustion. Before invoking a provider's second virtual
method, it searches the current registered-provider list for the same pointer.
Absent providers are skipped. After each invocation, nonzero lane-1 queue count
causes an early true return. Normal exit releases owned temporary storage,
restores the saved TLS word and mode, and returns whether that early success
condition occurred. Exception restoration is not established.

The pointer-membership recheck is real but does not independently pin lifetime or
prevent equal-address reuse. Query and execution callbacks run under the provider
guard; ordering/selection runs outside it. The ordering helper and metadata
meaning remain unknown, so no provider priority formula is claimed yet.

The context-submission helper is a separate stage: under its own guard it calls
two preparation helpers, stores the context as current, conditionally appends it
to a fixed-capacity ring, clears another pointer and calls an internal update.
After leaving the guard it calls two further helpers. Those final helpers and
context ownership remain unexpanded; none is named as a scheduler wake merely
from its position in the call sequence.

## Request-held references and reset lifecycle

Request initialization proves that the earlier producer's literal one is the
staging lane: the initializer stores that argument into request.lane and sets
request.kind to zero. It stores the key, completion callback, user pointer,
reprocess byte and an independently assigned context reference. It does not
initialize every byte of the request, so reset/pool invariants remain necessary.

The request's result and guard references retain resource entries through the
**low 24 bits of entry.flags**, not the separate entry.counter word used by the
acquired wrapper. Atomic operations modify the full 32-bit word; their release
test masks the decremented result:

```text
drop_request_entry(entry):
    previous = atomic_fetch_add_u32(entry.flags, -1)
    after = uint32(previous - 1)
    if (after & 0x00ffffff) == 0:
        release_request_reference(entry)
```

Initialization takes temporary and destination references, exchanges the old
result entry, and drops old and temporary references separately. Guard-entry
assignment increments the incoming entry before exchange and drops the old one.
Zero key uses the shared sentinel. Do not substitute the acquired-wrapper
`previous_count == 1` test for this masked post-decrement rule or merge the two
counters. No overflow protection for the packed count is established here.

Reset clears the key, drops result and guard entry references, and writes the
shared sentinel into both fields. It clears completion/alternate callbacks and
user pointer, resets lane to one and kind to one, clears request bytes 0x48
through 0x4a, and resets the context reference through an unexpanded assignment
helper. If an allocated processing context exists it calls context cleanup and
allocator release, then clears that pointer. Sentinel assignments in this reset
do not locally increment the sentinel's packed count.

Request return optionally invokes an opaque map operation when its registration
byte is set, performs reset, then conditionally appends to the free-object ring
under the ring guard. It increments the separate free-object count even if the
ring has no room and decrements the kind-zero request count according to the
**pre-reset** kind. No local growth occurs. Nested entry into the same ring guard
can occur from the previously decoded caller, so guard semantics remain relevant.

## Packed-reference release may defer cleanup

Under the resource-manager guard, this release helper rejects entry bit26 or a
nonzero low-24 count. It then rechecks the count and examines current record,
entry bit27 and a global byte. Several conditions route to the existing inner
recycler, which applies its own stronger counter/flag checks.

```text
release_request_reference(entry):
    enter(manager.entry_guard)
    if entry.flags.bit26 or low24(entry.flags) != 0:
        leave(manager.entry_guard)
        return
    if low24(entry.flags) != 0 or entry.record == null or
       entry.flags.bit27 or global_defer_override != 0:
        inner_recycle_if_eligible(manager, entry)
        process_now = false
    elif entry.flags.bit24:
        process_now = false
    else:
        atomic_set_bit(entry.flags, 24)
        grow_deferred_ring_by_16384_if_full()
        append_entry_if_room()
        process_now = manager.mode == 1 and current_context_mode() != 3
    leave(manager.entry_guard)
    if process_now:
        process_manager(manager)
```

Bit24 is set before the ring's growth/room outcome is known, and processing may
be requested even if insertion did not occur locally. Allocator/capacity
contracts remain open. This deferred ring is distinct from the key/record/entry
triple ring. A release can run manager processing synchronously after unlocking;
therefore reference drops are not necessarily constant-time or free of callbacks.
No arbitrary native destruction/modification safety is implied.

## Deferred cleanup rechecks revived references

The previously studied destruction-publication phase now closes the deferred
entry consumer. It takes the loading destruction-ring guard and manager entry
guard, rejects reentry when a manager busy word is nonzero, and otherwise sets
that word plus a global override byte before draining the deferred-entry ring.
Additional guarded global/sentinel setup is present; it is not interpreted as an
engine-wide pause or a standalone ownership protocol.

```text
consume_deferred_entries(manager, caller_collection):
    # Outer guard, busy and global-state setup omitted here.
    while signed32(manager.deferred_ring.count) > 0:
        entry = pop_deferred_entry()
        record = entry.record
        if low24(entry.flags) != 0:
            atomic_clear_bit(entry.flags, 24)
            continue
        if record != null:
            record.virtual_cleanup_hook()
            if manager.mode == 0:
                enqueue_loading_destruction(record)
            else:
                append(caller_collection, record)
        atomic_clear_bit(entry.flags, 24)
        inner_recycle_if_eligible(manager, entry)
    publish_staged_loading_destructions_and_notify_if_needed()
    # Normal exit clears manager busy and global override before guard release.
```

The low-24 reference check occurs after dequeue. A reference acquired since
queueing cancels this cleanup attempt; the queued bit is cleared so later release
can enqueue again. The hook and record routing are skipped in that case. A null
record with zero packed count still proceeds to the inner recycler. That recycler
rechecks the separate count and flags, so an attempted recycle does not prove
that the entry was actually freed or reused.

For a non-null record, the virtual hook precedes the mode read and routing. Mode
zero queues destruction for the loading thread; every nonzero mode appends to the
caller collection. Earlier manager-wrapper inspection establishes immediate
caller-side destruction only when its later mode read equals one. These conditions
must not be collapsed into a universal immediate-versus-deferred boolean.

The count is re-read on each loop iteration; unlike the triple consumer this is
not a captured batch count. No null-entry guard appears after the ring pop.
Callback effects, allocation success and ring invariants remain required
contracts. The executable decision helper models observed branch inputs only;
it neither pins records nor replaces the native CAS/recycler checks.

## Context reference assignment

The request context-reference assignment helper returns immediately when the
stored pointer equals the supplied pointer. Otherwise it increments the incoming
object's separate 32-bit counter by compare-exchange before atomically exchanging
the destination pointer. It decrements the displaced object's counter and calls
virtual slot 1 only when the pre-decrement value was one. Null incoming and old
pointers are handled independently.

```text
assign_context_reference(destination, incoming):
    if destination.pointer == incoming:
        return
    if incoming != null:
        atomic_increment_by_cas(incoming.counter)
    old = atomic_exchange_pointer(destination.pointer, incoming)
    if old != null and atomic_fetch_add_u32(old.counter, -1) == 1:
        old.virtual_release()
```

This establishes retain-before-publication and release-after-exchange locally.
It does not establish a weak-reference upgrade, acquisition from a concurrently
freed raw pointer, exception recovery, or overall context ownership. The request's
context reference and allocated processing context remain distinct fields.


## Ordered provider replacement and original-handle fallback

Static inspection now establishes the aggregate lookup around the previously
recovered provider-row reader. These names describe roles, not original classes.
The aggregate first consults its optional direct provider. It then visits an
ordered array of wrapper pointers, skipping null wrappers and wrappers whose
availability check returns null. The first provider that returns a replacement
handle wins. If every provider misses, the aggregate returns the original handle.

```text
select_replacement(aggregate, original, scalar_inout, flag_inout):
    if aggregate.primary != null:
        replacement = find_row(aggregate.primary, original.key,
                               scalar_inout, flag_inout)
        if replacement != null:
            return replacement
    for wrapper in aggregate.ordered_wrappers:
        if wrapper == null:
            continue
        provider = unwrap_if_available(wrapper)
        if provider == null:
            continue
        replacement = find_row(provider, original.key,
                               scalar_inout, flag_inout)
        if replacement != null:
            return replacement
    return original

find_row(provider, requested_key, scalar_inout, flag_inout):
    for row in provider.rows:
        if row.key != requested_key:
            continue
        scalar_inout.bits = row.scalar_bits
        flag_inout = row.flag
        if row.availability_pointer != null:
            return address_of(row.embedded_handle)
    return null
```

The output writes precede the row availability test. An unavailable matching row
can overwrite both outputs, and lookup continues through duplicate keys. Later
provider misses do not restore earlier output values. For example, if the primary
provider has an unavailable matching row with scalar 0.5 and all later providers
miss, the result is the original handle with scalar 0.5. That example uses a
synthetic scalar solely to demonstrate the observed write order.

The primary provider bypasses the wrapper availability helper. Therefore a
reconstruction must not apply the secondary-provider gate universally. Nor should
it convert a missing replacement into a missing original resource.

Both arrays use the previously observed relative-pointer convention: bit 62 set
and bit 61 clear means the stored value is relative to the pointer field;
otherwise it is direct. Counts use the low 29 bits. Wrapper entries are eight
bytes; provider rows are 56 bytes. The row byte-length multiply executes in
32 bits before address addition. This is a representation observation, not a
claim that corrupt or overflowing arrays are safe.

## Wrapper availability delegates to a context callback

The wrapper helper returns its stored pointer directly when its control word is
negative as a signed 32-bit integer. Otherwise it calls a predicate with that
pointer, returns null on false, and rereads the stored pointer on true.

```text
unwrap_if_available(wrapper):
    if signed32(wrapper.control_word) < 0:
        return wrapper.pointer
    if context_accepts(wrapper.pointer):
        return wrapper.pointer  # reread after callback
    return null

context_accepts(pointer):
    context = opaque_context_lookup(global_index)
    if context == null or pointer == null:
        return false
    descriptor = context.callback_descriptor
    if descriptor.word0 == 0 and descriptor.word1 == 0:
        return false
    if descriptor.callback == null:
        return false
    callback_context = address_of(descriptor)
    if descriptor.word1 != 0:
        encoded = u64(~descriptor.word0) XOR descriptor.word1
        if encoded < 256:  # unsigned comparison
            callback_context = descriptor.word1
    return descriptor.callback(0, callback_context, pointer)
```

Only the low return byte controls the wrapper branch. The callback's installation,
meaning and lifetime contract remain unresolved. In particular, this is not yet
proof of resource readiness, clip decoding completion or membership in a specific
animation graph. The control word lies beyond the eight-byte allocation returned
by the earlier acquire callback; these wrappers must not be identified with that
allocation without another ownership link.

## A caller consumes the replacement scalar conditionally

One direct caller initializes its output to float32 bits `ff7fffff`, the most
negative finite float32 value. It obtains an original handle through a virtual
method and initializes the lookup scalar from a context array using a stored byte
offset. It initializes the lookup flag to zero, obtains the aggregate through a
separate helper, and calls the replacement lookup above.

It then selects a 48-byte context row using a stored unsigned 16-bit index. The
selected handle's key is compared with a helper result from that row. If they
match, the sentinel output remains. If they differ, another row predicate is
called; only a false result copies the lookup scalar to the output.

```text
conditional_scalar_output(node, context, output):
    output.bits = 0xff7fffff
    original = node.virtual_get_handle(context.data)
    scalar = load_f32(context.scalar_array, node.scalar_byte_offset)
    flag = 0
    selected = select_replacement(get_aggregate(context.owner), original,
                                  scalar, flag)
    row = context.state_rows[node.state_index_u16]
    if row_identity(row) != selected.key:
        if not row_predicate(row):
            output = scalar
```

The lookup flag is not consumed in this caller. The scalar can reflect a failed
provider row even when the selected handle is the original. This caller proves a
conditional scalar use, but does not establish seconds, normalized time, blend
weight, duration, transition policy or a specific landing animation. The virtual
handle getter, aggregate getter, row identity and predicate remain explicit
interfaces. Other direct callers are leads, not inspected equivalents.


## Aggregate ownership and state callbacks

The aggregate getter follows two pointers: owner to an intermediate object, then
that object to the aggregate. It performs no local null check, allocation or
availability test. This establishes a context-owner route to the aggregate;
it still does not identify the acquired eight-byte resource wrapper with a
secondary-provider wrapper.

The preceding caller's row identity and predicate helpers share one callback
table. Each reads a first word from the embedded handle and an optional wrapper
through its backing object. It passes the wrapper's first pointer when present,
or null otherwise, as the first callback argument; the handle's first word is the
second argument. Separate table slots produce the compared key and tested byte.
Their installed targets remain unresolved, so neither is a decoded readiness or
playback-state predicate yet.

## Activation caller stores scalar and adjusts a settings byte

A second aggregate caller returns early when a context byte is already nonzero.
Otherwise it sets that byte to one before subsequent helpers, gets an original
handle through a virtual method, and initializes lookup scalar bits and flag to
zero. It selects a replacement and stores the scalar at the same node-selected
context offset used by the earlier conditional scalar reader.

It zero-initializes a six-byte settings block and asks another virtual method to
fill it. If selected and original handle pointers differ, it replaces settings
byte 3 with the byte comparison result `settings[3] != lookup_flag`. Pointer
equality leaves the settings byte unchanged. This is an inequality operation,
not a bitwise XOR for arbitrary non-boolean byte values.

```text
# Observed activation prefix. Later binding helpers remain opaque.
if context.activation_byte != 0:
    return
context.activation_byte = 1
prepare_context_row(context, node.state_index)
original = node.virtual_get_handle(context)
scalar_bits = 0
lookup_flag = 0
selected = select_replacement(aggregate_from_owner(context.owner), original,
                              scalar_bits, lookup_flag)
context.node_scalar_bits = scalar_bits
settings = six_zero_bytes()
node.virtual_fill_settings(context, settings)
if selected is not original:
    settings[3] = u8(settings[3] != lookup_flag)
prepare_selected(node, context, selected, settings)
bind_state_row(context.state_row, selected, settings[0], settings[1])
```

The inspected continuation copies settings bytes 2, 3 and 5 into state-row
bytes, passes selected handle and a packed settings/scalar block into a binding
helper, then performs further resource and mode-dependent work. These calls are
not expanded by the prefix pseudocode. The activation byte's reset owner and
cadence remain unknown, so this gate cannot yet be called once-per-frame or
once-per-clip. The six settings bytes have no established semantic names.

The independent `engine.animation_provider` module implements only the earlier
ordered lookup contract over synthetic caller-owned objects. It retains scalar
bits exactly and accepts an explicit availability callback. Tests cover primary
precedence, failed-row writes, duplicate keys, skipped wrappers, and a callback
that changes the wrapper pointer before the required reread. These tests validate
our local adapter, not original clip playback or native concurrency.


## Tagged endpoint conversion

The state-row binding helper initializes an endpoint pair to zero and a
resource-callback scalar. It stores a metadata object obtained from another
resource callback. When metadata exists and either of the first two settings
bytes is nonzero, it searches for a child with raw type code `ffffff90`. If that
child exists, it obtains a limit through the metadata object's virtual method.
Each nonzero settings byte is then used as a tag to select an endpoint.

The child accessor reports a record count, reads one byte per record for tag
comparison, and returns an unsigned 16-bit value for the first matching record.
The exact conversion is:

```text
find_tagged_endpoint(child, tag, limit, output):
    count = child.accessor.count(child.data)
    for index in unsigned_range(count):
        record_tag = child.accessor.read_byte(child.data, index, width=1)
        if record_tag == tag:
            encoded = low16(child.accessor.value(child.data, index))
            decoded = float32(float32(encoded) / float32(120.0))
            output = MINSS(limit, MAXSS(+0.0, decoded))
            return true
    output = +0.0
    return false
```

The divisor is read from the frozen image as float32 120.0. No seconds or frame
rate is inferred from that number. Integer-to-float conversion is exact over the
unsigned 16-bit domain. MINSS chooses its source operand for equal or unordered
operands: a NaN limit yields the decoded value, and equal signed zeros choose the
decoded positive zero. A negative limit can produce a negative result because the
zero lower bound is applied before the limit cap.

The caller ignores each lookup's boolean result. Thus a nonzero missing end tag
changes the initially supplied end value to zero. After both lookups, an ordered
start greater than end restores start to zero and rereads the resource default
end callback. Equal or unordered endpoints do not trigger that fallback.

```text
initialize_endpoints(row, selected, start_tag, end_tag):
    row.metadata = resource_metadata(selected)
    row.start = +0.0
    row.end = resource_default_end(selected)
    if row.metadata == null or (start_tag == 0 and end_tag == 0):
        return
    child = find_child(row.metadata, raw_type=0xffffff90)
    if child == null:
        return
    limit = row.metadata.limit_source.virtual_value()
    if start_tag != 0:
        find_tagged_endpoint(child, start_tag, limit, row.start)
    if end_tag != 0:
        find_tagged_endpoint(child, end_tag, limit, row.end)
    if ordered_greater(row.start, row.end):
        row.start = +0.0
        row.end = resource_default_end(selected)  # a fresh callback
```

A null limit-source object reaches a failure helper and trap, rather than a
zero-limit fallback. The metadata callback returns an interior pointer which the
local adapter adjusts backward by eight bytes when non-null. Child type naming,
accessor implementation, default/limit units and selected resource identity remain
open. The standalone tagged-endpoint helper tests conversion, first-match order,
missing tags, capping and floating-point operand rules with synthetic records.

## Binding callback replacement order

The packed endpoint/settings block reaches a binding helper. If the destination
contains an old token, the helper invokes a callback with the old owner's optional
wrapped pointer and token, then clears the token. It stores the new owner before
calling a creation/binding callback with the new owner's optional wrapped pointer,
the selected resource's optional backing pointer, and the packed settings block.
It stores that callback's returned token, including a null result.

```text
replace_binding(destination, new_owner, selected, settings):
    if destination.token != null:
        callbacks.release(optional_wrapped_pointer(destination.owner),
                          destination.token)
        destination.token = null
    destination.owner = new_owner
    destination.token = callbacks.bind(optional_wrapped_pointer(new_owner),
                                        optional_backing_pointer(selected),
                                        settings)
```

There is no local same-resource skip or rollback to the old token on a null bind
result. Callback internals may impose additional behavior. The callback names
here describe their observed positions, not proven allocation/destruction
semantics. This ordering alone establishes neither native lifetime safety nor
completion of resource loading.

The activation preparation helper can perform an earlier binding with both tag
bytes forced to zero when its context identifier differs from a global value.
It copies the other settings, performs an opaque context/evaluation path, and on
success updates another scalar and clears another byte. The outer activation
caller subsequently performs the tag-aware binding described above. Therefore
one activation can invoke the binding path twice. The global identifier and
opaque evaluation result must be resolved before assigning a frame or event
meaning to the preliminary path.


## Registered evaluator callbacks and error-resource fallback

Name registration, slot setters, and the installation caller now connect the
previously opaque callback slots to these names and implementations:

| Interface | Registered name | Inspected local behavior |
| --- | --- | --- |
| Resource scalar | GetAnimationResourceLength | Resolve resource; return its stored float length |
| Resource metadata | GetAnimationData | Resolve resource; return its stored data pointer |
| Binding creation | AcquireEvaluator | Obtain a pooled evaluator or allocate one; initialize and register it with the owner |
| Binding release | ReleaseEvaluator | Remove evaluator from owner collection; hand it to the pool-release helper |
| Bound key | GetAnimationId | Read evaluator resource entry's key |
| Bound predicate | IsPlayingErrorAnimation | True when that key is zero or equals the global error resource key |

These are recovered registration strings, not names inferred solely from use.
The registered length name supports interpreting the default endpoint as resource
length. The physical time unit still needs a producer or playback-consumer check.
The metadata adapter still applies the previously documented minus-eight
adjustment to the returned data pointer.

```text
GetAnimationId(owner_unused, evaluator):
    return evaluator.resource_entry.key

IsPlayingErrorAnimation(owner_unused, evaluator):
    key = evaluator.resource_entry.key
    return key == 0 or key == global_error_resource_entry.key
```

Consequently the earlier conditional scalar reader emits its scalar only when the
selected key differs from the current evaluator's animation ID and the evaluator
is not playing the error animation. Equality and error animation both retain the
negative-finite sentinel. This supersedes the anonymous predicate interpretation;
it does not yet identify the scalar as blend weight or transition duration.

Resource length, data and evaluator acquisition use the same resource resolver.
It accepts a resource record pointer only when the shared entry's sign bit is set
and its record pointer is non-null. Otherwise it retains the global error entry,
atomically replaces the wrapper's entry, releases the displaced separate
reference, and rereads the replacement through the same sign-bit gate.

```text
resolve_resource(wrapper):
    record = wrapper.entry.record if wrapper.entry.flags.bit31 else null
    if record != null:
        return record
    replacement = global_error_resource_entry
    atomic_increment(replacement.separate_reference_count)
    old = atomic_exchange(wrapper.entry, replacement)
    if atomic_fetch_add(old.separate_reference_count, -1) == 1:
        if low24(old.flags) == 0:
            release_entry_if_eligible(old)
    return wrapper.entry.record if wrapper.entry.flags.bit31 else null
```

This is a mutating fallback, not a read-only query. The callers dereference its
result without a local null guard, so a valid published error resource is an
external invariant. The resolver does not wait for loading to complete. Once it
replaces the wrapper entry, later publication of the displaced entry does not by
itself reattach that wrapper. Rebinding requires another writer.

AcquireEvaluator obtains owner-related objects through two opaque lookups, then
tries a pool. If empty it allocates 1152 bytes aligned to 16 and constructs the
evaluator. It resolves the selected resource, initializes the evaluator, appends
it to the owner's collection and returns it. The observed allocation-failure
branch passes null onward to initialization; no graceful-failure guarantee is
claimed. ReleaseEvaluator removes the token from that collection before passing
it to the pool helper. The pool's retention/destruction policy remains open.

The initializer first invokes a resource-assignment helper with a true byte, then
passes the packed start/end floats to a range helper. It writes packed settings
byte 8 low bit into evaluator flag bit 0 and settings byte 10 low bit into flag
bit 1, preserving other bits. In the upstream six-byte activation settings these
are bytes 3 and 5 respectively. Packed byte 9 is not read in this initializer.
The two bits' semantic names remain unresolved; the remaining context setup
helper may perform additional work.


## Effective range and tick quantization

The range setter stores two float32 requested endpoints and sets evaluator flag
bit 5. It performs no local validation or cache rebuild. A later consumer chooses
those endpoints when bit 5 is set, otherwise zero and resource length. It uses
float32 epsilon `9.999999747378752e-06` and the following finite-input rules:

```text
start, end = requested_range if custom_range else (0, resource_length)
if abs(f32(start - end)) <= epsilon:
    start = MAXSS(f32(start - context_backoff), +0.0)
else if abs(end) <= epsilon:
    end = resource_length
if start >= end:
    start, end = 0, resource_length
start_tick = low16(CVTTSS2SI64(f32(f32(start * 120.0) + 0.5)))
end_tick = low16(CVTTSS2SI64(f32(f32(end * 120.0) + 0.5)))
```

The nearly-equal branch precedes the near-zero-end branch. Its backoff comes from
one of two owner-context fields selected by another object's flag bit 58. Missing
owner/context supplies zero. The field is not yet established as frame delta,
so the independent kernel requires it as an explicit input. Negative backoff or
other invalid inputs are not repaired by an invented clamp.

The final native comparison uses COMISS/JB: strictly less or unordered skips the
full-range reset. The near-equality and near-zero tests likewise skip their
repair when unordered. The standalone range kernel currently accepts finite
float32 inputs only; it does not claim native NaN behavior. It preserves the
32-bit arithmetic stages and low16 tick storage. There is no local saturation to
65535; values beyond that range wrap in the stored word after conversion. This
complements the earlier unsigned16 / 120 decoding without proving seconds.

When the consumer's reset argument is nonzero, it also sets two adjacent float
state words to zero, updates a progress-like scalar and its copy with
`MINSS(f32(end-start), old_scalar)`, fills two index-cache arrays with all-one
bytes, and invokes another reset helper with sentinel 65535. This does not apply
a zero lower bound to the old scalar. The field's producer and remaining reset
helper still need decoding before it can be called a complete playback clock.

The separate resource-assignment helper stores the resource pointer, looks up its
shared entry, and transfers a packed low24 reference into the evaluator's entry
field. Drops reaching low24 zero use the previously decoded deferred-release
helper. Its optional reset clears the progress-like scalar and four following
words except the first following word, which receives float32 1.0. These fields
are distinct from the requested/effective endpoints and tick words.

A further state-change helper was inspected as a lead. It uses evaluator bit 4,
an integer selector and a float comparison to skip unchanged work. Its active
path temporarily changes the progress-like scalar, invokes an opaque operation,
restores a capped previous value, and can restore requested endpoints followed by
the range/cache reset. It is not yet identified as seek, synchronization, or an
animation mode, so none of those semantics enter the executable model.


## Position setters and timestamp cursor boundaries

Two explicit setters write the evaluator's relative position. One multiplies the
requested fraction by effective range duration before capping; the other caps a
requested absolute offset. Both use MINSS with the requested value as source,
so neither provides a zero lower bound. These are explicit writes, not proof of
the automatic playback clock's update rule.

```text
set_fraction(fraction, preserve_history):
    duration = f32(end - start)
    position = MINSS(duration, f32(duration * fraction))
    if not preserve_history:
        position_copy = position
        two_history_words = 0
    invalidate_both_index_caches()

set_offset(offset, preserve_history, invalidate):
    position = MINSS(f32(end - start), offset)
    if not preserve_history:
        position_copy = position
        two_history_words = 0
    if invalidate:
        invalidate_both_index_caches()
```

The boolean parameter names above describe observed effects. They are not
recovered API names. The two history words' precise meanings remain unknown.

A separate reset helper computes absolute position as float32 relative position
plus effective start, then walks selected timestamp tracks. It filters each
track by a mask intersection. A matching track's unsigned16 timestamps are divided
by float32 120.0. The first timestamp greater than or equal to current position
sets the cursor to the preceding index, or all-one bits for index zero. If no
such timestamp exists, it writes the count itself. An empty track writes zero.
Unselected tracks keep their old cursor.

```text
reset_cursor(times, absolute_position):
    for index in range(count):
        if f32(times[index] / 120.0) >= absolute_position:
            return index - 1  # index0 becomes native ffffffff
    return count
```

Another track consumer has a dispatch branch and a cursor-only branch. The latter
starts at zero for the all-one sentinel, otherwise unsigned cursor+1, and advances
while decoded timestamp is less than or equal to current absolute position. It
does not rewind when position decreases. Thus exact equality differs between
reset and advancement, and duplicate timestamps at the boundary are all consumed
by the forward path. Do not replace reset's exhaustion result with count-1.

```text
advance_cursor(times, absolute_position, cursor):
    index = 0 if cursor == 0xffffffff else u32(cursor + 1)
    while index < count:
        if f32(times[index] / 120.0) > absolute_position:
            break
        cursor = index
        index += 1
    return cursor
```

Reset and forward traversal read different count fields in the track. Their
relationship remains unproved. The synthetic cursor helper takes the chosen
sequence explicitly and accepts finite positions; it is not an event dispatcher.
The native COMISS branches differ on NaN and no NaN equivalence is claimed.

The dispatch branch requires a nonzero caller gate, a compatible track level,
a mask intersection, and evaluator flag bit 3. It passes current position, cached
cursor, resource, start/end tick words and other context to an unresolved helper.
A failed gate still takes the cursor-only branch, so skipping delivery does not
necessarily preserve the cursor. The original temporal clock producer, flag
bit 0/1 consumers, and dispatched payload semantics remain open.


## Timestamp payload dispatch

The previously unresolved track dispatcher returns immediately when its caller
mode is zero. Otherwise it visits timestamps after the current cursor until a
decoded timestamp exceeds current absolute position. It writes the cursor before
loading and filtering the corresponding payload. Missing payloads, missing payload
resource pointers, boundary exclusions, blocked entries and missing recipients
all leave that cursor advanced.

For a payload whose metadata lookup succeeds, three byte flags apply. Raw
unsigned16 timestamp is shifted right by one for the boundary comparisons, even
though the due-time comparison divides the unshifted timestamp by 120.0. Bit 2
permits the start-boundary entry; bit 1 permits the end-boundary entry. Mode exactly
one additionally requires bit 0. Other nonzero modes bypass only the bit-0 test.
If metadata lookup returns null, all three metadata tests are bypassed.

```text
for each due index after cursor:
    cursor = index
    payload = track.payloads[index]
    if payload == null or payload.resource == null:
        continue
    metadata = lookup_payload_metadata(payload.resource)
    if metadata != null:
        boundary_word = raw_timestamp[index] >> 1
        if not metadata.bit2 and boundary_word == start_tick:
            continue
        if not metadata.bit1 and boundary_word == end_tick:
            continue
        if mode == 1 and not metadata.bit0:
            continue
    if payload.blocker != null and payload.blocker.word0 != 0:
        continue
    if recipient == null:
        continue
    if classify(payload, classification_argument) and output_flag != null:
        output_flag = 1
    payload.virtual_prepare(mask)
    dispatch(context, payload, recipient, owner)
```

The classification result does not gate delivery: it only sets an optional output
byte, which is not cleared locally. Virtual preparation precedes the dispatch
helper. The payload behavior and dispatch helper's side effects remain unresolved.
No rewind, retry queue, exactly-once guarantee or event-name interpretation is
established by this local routine. The right shift is preserved without assuming
an undocumented doubled timestamp unit.

The independent dispatch-gate helper covers only these post-cursor conditions.
It does not send events. Tests distinguish missing metadata from zero flags,
mode one from other nonzero modes, and the independent start/end boundary bits.
A full reconstruction must advance the cursor before applying these gates.

A concrete wrapper around the fraction setter forces history reset, optionally
runs the masked cursor reset with an all-one mask, and invalidates a third cache
array afterward. Thus setting position can reset the cursor explicitly, while
ordinary failed delivery does not. That wrapper's registered name and the third
cache's element meaning remain leads.


## Timestamp output is a retained batch, not immediate delivery

Further inspection resolves the helper previously called `dispatch` in the
payload pseudocode. It appends to three parallel arrays in the supplied context:
a raw payload pointer, a retained shared recipient entry, and a retained shared
owner entry. No payload invocation occurs in that helper. The virtual preparation
call before it remains a separate possible source of side effects.

```text
enqueue_timestamp_payload(context, payload, recipient_record, owner_record):
    append_raw_pointer(context.payloads, payload)
    recipient = lookup_shared_entry(key=0, record=recipient_record)
    append_retained_entry(context.recipients, recipient)
    release_temporary_separate_reference(recipient)
    owner = lookup_shared_entry(key=0, record=owner_record)
    append_retained_entry(context.owners, owner)
    release_temporary_separate_reference(owner)
```

The retained-entry append copies the entry pointer into its new slot and
increments the entry's separate reference count. Temporary release uses the
previously decoded count-one and packed-low24-zero gate. Thus the appended
recipient and owner references survive the temporary lookup references locally.
The payload append performs no reference increment here. Its lifetime may be
owned elsewhere and cannot be inferred from the other two arrays.

All three appends are sequential. There is no local transaction, shared count
commit or rollback across them. Each array has its own storage and count. A batch
consumer must not assume a concurrently observed triple is complete without an
additional synchronization contract. The consumer, clear/drain ownership and
thread scheduling remain open.

Both append variants use the same capacity arithmetic. Capacity is the low 14
bits of the header; count is an unsigned16 word. When count+1 exceeds capacity,
proposed capacity is:

```text
growth = 4 if capacity < 24 else floor(capacity / 3)
proposed = min(16383, capacity + growth)
if proposed > capacity:
    resize_storage(proposed, element_size=8, alignment=8)
count = u16(count + 1)
write_slot_using_incremented_index()
```

The native append proceeds without a post-resize success or remaining-room check.
This is an allocation/capacity invariant, not a safe overflow policy to imitate in
the reconstruction. The public model does not allocate native arrays or claim
failure recovery for this path.

## Payload metadata lookup is an interval type check

The metadata helper calls the supplied object's descriptor virtual method and
compares two unsigned16 descriptor bounds with a global target descriptor. It
returns the original object pointer when the object's interval is contained in
the target interval, otherwise null. A null input returns null.

```text
payload_metadata(object):
    if object == null:
        return null
    actual = object.virtual_descriptor()
    if target.low <= actual.low and actual.high <= target.high:
        return object
    return null
```

These comparisons derive from signed32 differences between zero-extended16-bit
values; the differences cannot overflow. The helper does not allocate, decode,
load, or return a separately stored metadata object. This supersedes the earlier
opaque lookup description. The target type's semantic name remains unproven, and
inverted intervals are not separately rejected here. The returned object's flag
byte supplies the previously decoded event-boundary permissions.

The next evidence needed is the parallel-array consumer. Until that is traced,
queued payloads are not evidence that a footstep, sound, animation notification,
or gameplay effect was delivered.


## Three-array destruction contract and an owner candidate

A constructor initializes three adjacent array headers with stride 144 bytes,
each with inline storage for 16 eight-byte entries. Its destructor passes the
first header to a helper that matches the timestamp batch layout. This is an
owner candidate supported by constructor/destructor structure; the producer's
context pointer has not yet been proved to refer to this particular object.

The batch destructor processes the owner-reference array first, then the
recipient-reference array. It finally frees the payload-pointer array's storage
when that storage is externally allocated. It does not walk the payload pointers
or invoke payload destructors locally.

```text
destroy_batch(batch):
    destroy_entry_array(batch.owners)
    destroy_entry_array(batch.recipients)
    if not batch.payloads.header.bit15 and batch.payloads.data != null:
        free_storage(batch.payloads.data)

destroy_entry_array(array):
    if not array.header.bit14:
        for slot in captured_range(array.data, array.count):
            entry = slot.pointer
            if atomic_fetch_add(entry.separate_count, -1) == 1:
                if low24(entry.flags) == 0:
                    release_entry_if_eligible(entry)
    if not array.header.bit15 and array.data != null:
        free_storage(array.data)
```

Bit 14 suppresses element cleanup; bit 15 suppresses storage deallocation. They
are independent gates. Constructor header value `8010` therefore starts with
inline-storage protection, capacity 16, zero count and element cleanup enabled.
The reference-release walker captures the end pointer, advances eight bytes per
entry, and does not null slots or clear the array count. There is no per-entry
null guard. This is a destruction path, not an idempotent drain API.

The owner candidate's outer destructor performs other cleanup before and after
this batch destruction. Nothing in these helpers proves delivery before teardown,
scheduler synchronization, reentrancy safety or a complete producer/owner join.
The delivery consumer remains the highest-value next target; the exact cleanup
contract can now constrain that investigation.


## Producer-to-owner batch connection

A setup routine now joins the previously compatible owner layout to the actual
producer path. It configures the embedded evaluator and supplies the address of
the owner's first batch array in a context descriptor. Evaluator initialization
copies that descriptor pointer into the field later read by the timestamp track
consumer. The consumer forwards it through the payload filters to the three-array
enqueue helper. The constructor/destructor layout is therefore connected to a
static producer path, rather than supported only by offset coincidence.

```text
owner setup:
    evaluator = owner.embedded_evaluator
    descriptor.batch = address_of(owner.timestamp_batch)
    initialize_evaluator_context(evaluator, descriptor)

evaluator initialization:
    evaluator.batch = descriptor.batch

later timestamp processing:
    enqueue_timestamp_payload(evaluator.batch, payload, recipient, owner_record)
```

This establishes the pointer route for this setup path, not live identity in a
captured player session or a universal route for all evaluators. Another earlier
acquisition path supplies its own context descriptor.

## Evaluator context initialization order

The initializer copies the owner, auxiliary context and batch pointers, along
with two 16-bit track masks. Descriptor flag bit 2 controls evaluator flag bit 3,
which was previously observed gating timestamp payload processing. This joins
that delivery gate to an explicit setup input without inventing its semantic name.

It allocates two four-byte cursor arrays from resource counts and initializes
every element to all-one bits. One count comes from a separate resource field;
the timestamp array count matches the timestamp track-pointer array count. It
then optionally releases and reacquires an auxiliary binding through the supplied
context, forwarding evaluator flag bits 0 and 1 separately.

```text
initialize_evaluator_context(evaluator, descriptor):
    copy_owner_auxiliary_batch_and_masks(evaluator, descriptor)
    evaluator.flags.bit3 = descriptor.flags.bit2
    evaluator.optional_pointer = null
    clear_two_short_fields()
    resize_and_fill_first_cursor_array(resource.first_count, 0xffffffff)
    resize_and_fill_timestamp_cursors(resource.timestamp_track_count, 0xffffffff)
    if evaluator.auxiliary_context != null:
        release_previous_auxiliary_binding_if_present()
        evaluator.auxiliary_binding = acquire_auxiliary_binding(
            resource, evaluator.flags.bit0, evaluator.flags.bit1)
        opaque_post_binding_setup(evaluator)
    resolve_effective_range(reset_history=false)
    reset_timestamp_cursors(mask=0xffff)
    opaque_followup(evaluator)
    conditionally_register_evaluator_with_owner_component()
    if evaluator.flags.bit4:
        temporarily_clear_bit4()
        reapply_state_change_with_preserve_argument()
```

The two allocations and subsequent operations have no local transactional rollback
in the inspected routine. Auxiliary binding semantics, component registration and
the final bit-4 operation remain opaque. The ordering establishes that initial
cursor state is derived after range resolution; it does not establish the
per-frame update order or native deterministic replay.

The owner setup path subsequently sets evaluator offset to zero with history reset
and cache invalidation, then resets masked timestamp cursors again. Repeated cursor
reset in that path is observed behavior, not a reason to remove one call from a
reconstruction before its other effects and callers are understood.
