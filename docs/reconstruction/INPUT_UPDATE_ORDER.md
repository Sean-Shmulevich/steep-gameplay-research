# Input service update order

This note joins the reconstructed cached-button query and timestamp updater to
their inspected callers. It establishes local instruction order, not an
input-to-physics scheduling guarantee. Current source is the private analyzed
image; no live process was accessed.

## Holder cycle

RVA `0x11789f0` brackets a holder update with two calls through the same helper
sequence. Functional names below describe the role in this pseudocode; they
are not recovered symbols.

```text
context = helper_115dd60(holder)
other = helper_1161b90(holder)
helper_1176be0(other, context)

holder.current_refresh = holder.pending_refresh   // byte +d6 <- byte +d5
holder.pending_refresh = 0
update_holder(holder)

context = helper_115dd60(holder)                  // reacquired, not reused
other = helper_1161b90(holder)
helper_1176be0(other, context)
```

The second helper pair executes after the nested update returns. This does not
establish lock semantics or a snapshot: those helper effects remain open.
A nonzero pending refresh is consumed into the current-cycle field, then
cleared before polling. No evidence here says which producer sets it.

## Nested holder update

RVA `0x1178a60` performs the following sequence:

```text
receiver = holder.link_e8.object_at_8
receiver.virtual_110()
if holder.pending_token_at_130 != -1:
    receiver = reload holder.link_e8.object_at_8
    if receiver.virtual_190(holder.pending_token_at_130):
        holder.pending_token_at_130 = -1
        receiver = reload holder.link_e8.object_at_8
        receiver.virtual_118()

if holder.service_at_d8 != null:
    if holder.current_refresh != 0:
        holder.service_at_d8.initialized_byte_1329 = 0
    service = reload holder.service_at_d8
    poll_service(service)                         // RVA 11785c0

helper_11790a0(holder)
if holder.current_refresh != 0:
    helper_116ff00(holder.link_e8)
```

The unknown virtual methods are deliberately not named device-acquire,
completion-fence or frame-start APIs. Their effects are not decoded here.
Repeated receiver/service reads are preserved because callbacks may mutate
links. A missing service skips polling but does not skip helper_11790a0 or
the optional final helper. The pending token is cleared before virtual_118.
The current-refresh byte is read again after the nested calls; treating its
initial value as immutable would require a separate mutation assumption.

Helper_11790a0 clears holder+0x138 and +0x140, then conditionally obtains two
pairs of float values through a global object. Those fields are not identified
as player steering or motion input. This follow-up is not proof of action-map
evaluation. The final helper and bracketing calls remain investigation leads.

## Service poll and cache edges

The service call first invokes helper_116dac0. If initialized_byte_1329 is zero,
it calls helper_1158270, stores that result at +0x132c, sets the byte to one,
and invokes helper_1178d30. The earlier holder refresh can therefore force
this initialization path on the next nested service call.

It then copies current key bytes and the current special packet to their
previous arrays. Subsequent focus, service-enable and acquisition gates decide
whether it polls, clears state, returns early, or reaches the edge timestamp
updater. The ordinary enabled path reaches timestamp refresh only after polling.
The timestamp updater runs before later key/packet change comparisons and
notifications. See [polling and copy order](MOTION_MEMBERSHIP_OBSERVATION.md#input-cache-polling-and-copy-order)
and [edge semantics](MOTION_MEMBERSHIP_OBSERVATION.md#cached-input-timestamp-edges).

This sequence explains three distinct observation cases:

- Poll and timestamp update complete: previous arrays describe cache state at
  the copy point, while current arrays include subsequent polling effects.
- An early return after cache clearing: clock/timestamp fields may remain old
  despite current bytes changing. A sample cannot assume every change was stamped.
- Holder refresh: initialization precedes the cache-copy and poll sequence.
  Its effects require decoding before replaying the entire holder cycle.

## Call-graph boundary and next experiment

A direct relative call at RVA `0xf9078a` invokes the holder cycle when an outer
object's byte +0xaf is nonzero. The inspected surrounding region subsequently
queries services and applies additional conditions. It is not established as
the normal physics update loop. The static search found no direct tail-jump to
the holder-cycle entry; indirect calls or registration paths may still exist.
Search absence is not proof of a unique runtime caller.

Useful observation boundaries, once live testing is available, are holder
entry/return, service poll entry/return, and timestamp-updater entry/return.
Record process/thread identity, holder/service identities, refresh bytes,
current/previous clocks and changed-key indices. Join those events with the
existing action and substep observations using a common sequence counter.
Do not infer order from unrelated wall-clock samples or assume a pause means
all input work has stopped. No hooks or capture have been installed for this
proposal.

Offline next steps are to decode the bracketing and final helper effects,
identify refresh-byte writers, and find indirect holder-cycle registration.
The [static receipt](../../native/snow_host/input_update_order_evidence.json)
records inspected span hashes and direct call sites. It is not an execution
receipt or a scheduler-equivalence test.

## Cache exchange around the holder cycle

The previously unknown bracketing helper at RVA `0x1176be0` is now decoded as
a field exchange. It immediately returns for identical object pointers.
Otherwise it swaps selected fields between the two objects, with no calls,
locks or allocation. The [independent raw-byte kernel](../../engine/action_cache_exchange.py)
models distinct, disjoint object snapshots and preserves all float bit patterns.
It does not model partial memory overlap or infer object lifetime.

The exact exchanged half-open ranges are:

| Range | Observed contents |
|---|---|
| +0x10 .. +0x50 | Two sets of 32 individual bytes |
| +0x50 .. +0x60 | Two uint64 fields |
| +0x60 .. +0x160 | 32 uint64 fields |
| +0x160 .. +0x168 | One uint64 field |
| +0x168 .. +0x1e8 | 32 four-byte scalar fields, moved without arithmetic |
| +0x1f0 .. +0x210 | Two four-lane vectors |
| +0x7c8 .. +0x7d8 | Two sets of eight bytes |
| +0x7d8 .. +0x818 | Eight uint64 fields |

These combine to three contiguous byte ranges in the portable kernel. Every
other byte in the inspected span remains attached to its original object.
The scalar/vector offsets overlap the cache layout used by the reconstructed
vector-action source: scalar values at +0x168 and vectors at +0x1f0. This is a
static layout connection. It does not identify the actual runtime objects
selected by the two holder helper calls.

The holder cycle therefore performs a cache exchange before its nested update
and another afterward. Two exchanges of unchanged, identical pairs restore
the original bytes. That observation must not be generalized to the real
cycle: callbacks can change fields or selectors, and the holder reacquires
both object pointers before the second exchange. An intervening field update
may be transferred to the other object by the second exchange. A passive
reader can also observe partially exchanged fields because no synchronization
is present in this helper.

The [exchange receipt](../../native/snow_host/input_cache_exchange_validation.json)
records 512 complete original-routine cases without substituted calls,
including 64 identical-pointer no-ops. Both complete 0x818-byte snapshots match,
including bytes that should not change. Random raw patterns cover non-finite
float encodings without interpreting them as numbers. Public tests also check
that two detached exchanges restore both inputs.

This supersedes the earlier unknown classification of helper_1176be0. The
selectors at `0x115dd60` and `0x1161b90` use holder indices +0x230 and +0xd0;
both have a zero-index branch returning holder.link_e8.object_at_8. Nonzero
selection and caller lifetime still need reconstruction. These selector
branches are the next static leads for determining which cache is exchanged
when, before claiming a publication or synchronization boundary.

## Ring-index cache selectors

The selectors at RVAs `0x115dd60` and `0x1161b90` use the same arithmetic with
holder offsets +0x230 and +0xd0 respectively. They obtain the root object through
holder+0xe8, then link+8. An offset of zero returns that root directly, without
consulting ring metadata. A nonzero offset selects a cache through a record:

```text
current = root.uint32_at_828
count = root.uint16_at_836
index = wrap_u32(current + holder_offset) % count
record = root.pointer_at_82c + index * 0x440
cache = record.first_uint64
```

The addition wraps to uint32 before the unsigned division. Signed-looking
values such as 0xffffffff are treated as their 32-bit bit patterns, not
Python negative indices. The two offsets are not themselves array indices.
For example, current=0xffffffff and offset=2 yields wrapped sum 1, selecting
record 1 when count is 3. Offset zero still returns the root even if the ring
is empty or its current index would point elsewhere.

[`select_input_cache`](../../engine/action_cache_selection.py) implements the
stable-snapshot rule and returns the selected record index with its cache
identity. It preserves null and repeated record-cache values rather than
inventing a fallback. It rejects nonzero offset with zero count; the original
selector would attempt division by zero. Native record lookup additionally
checks index<count, but the selector then dereferences its result without a
null check. These routines do not provide safe recovery from invalid metadata.

The original selector reloads the holder link/root before record lookup, after
reading the current index/count from the earlier root. Concurrent root or count
changes are outside the stable-snapshot kernel and need guarding in any passive
reader. No lock, ownership hold or synchronization boundary was found here.

The [selector receipt](../../native/snow_host/input_cache_selection_validation.json)
executes both complete selectors and their record lookup helpers without
substituted calls. All 360 selected pointers match across empty zero-offset
paths, ring counts 1/2/3/7/16, wrap boundaries, large offset bit patterns, null
cache values and records sharing the root cache. It does not validate the
producer of the current ring index or either holder offset.

This resolves the nonzero-selector gap in the cache-exchange section. If both
holder offsets are zero, both helpers return the root and the exchange is a
no-op. Equal or aliased selected cache pointers also produce a no-op. Distinct
selected pointers cause the field exchange already reconstructed. Next:
identify ring-index/offset writers and determine whether changes denote input
history, alternate contexts or another mechanism before assigning generation
semantics.


## Cache-index writer and selection policy

Static inspection now connects the final holder helper `0x116ff00` directly to
index writer `0x11afd30`. This is the same record container used by the cache
selectors: pointer +0x82c, uint16 count +0x836, stride 0x440, and current index
+0x828. The writer does **not** advance the index by one. It scans a configured
range and chooses a record according to an external query result.

The following names describe fields, not recovered class or enum names. All
indices and scan bounds are unsigned 32-bit values; record count is uint16.
The scan reads record+0x420 as the query argument. Its output buffer is a local
stack slot whose contents are not consumed by this caller.

```text
candidate = object.scan_begin_838
while candidate < object.scan_end_83c:
    result = unresolved_query(records[candidate].id_420, temporary_output)
    if result == 0:
        if candidate < object.record_count_836:
            select(candidate)
        return
    candidate = wrap_u32(candidate + 1)

if object.fallback_flag_840 > 0:
    candidate = object.scan_end_83c
    if candidate < object.record_count_836:
        select(candidate)
    return

if object.record_count_836 > 0:
    select(0)
notify_helper_1174880(global_holder, 1)
service = helper_1161170(reload_global_holder())
helper_1174e00(service, 1)

select(candidate):
    old = object.current_index_828
    object.current_index_828 = candidate
    unresolved_helper_117c440()
    new = object.current_index_828  # reload after unresolved call
    if old != new and global_holder != null:
        helper_91f2f0(global_holder + 0x70, old, new)
```

The fallback flag comparison is unsigned: any nonzero bit pattern takes the
scan-end fallback. Finding a zero query result outside record count ends the
routine without trying a later record or fallback. The scan itself has no
record-count bounds check before dereferencing each record; metadata validity
must come from elsewhere. The zero fallback still performs its final two
notifications when count is zero. Other branches do not perform those final
notifications. `select` calls its unresolved helper even when old and assigned
indices are equal. The later old/new comparison uses a fresh read, so treating
that helper as a no-op would discard possible behavior.

This establishes a selection policy, not its semantic purpose. A query return
of zero is not yet proved to mean available, connected, active, or successful.
The query target `0x1c34f3c` and post-assignment helper `0x117c440` lead into
unresolved code paths in the inspected image. They are not replaced with
invented device behavior. Historical-buffer rotation is unsupported by this
writer; alternate input contexts or devices remain hypotheses.

### Placement within the final holder helper

`0x116ff00` first calls helper `0x1179350`, obtains the current record through
`0x119ed40`, and passes record+0x0c to a helper with destination link+0x78 and
size argument 0x104. It then calls `0x11b0160(root, 0)` and `0x11ada50(root)`,
clears root+0x858, prepares link-local collections, and invokes virtual +0x20
on the receiver at link+0. The arguments include callback `0x115a650`, value 4,
the link, and a final value 1. These operations are not yet decoded as a whole.

Only a nonnegative signed return from that virtual call reaches the collection
processing and helper `0x1174150(link)`. Only a false low-byte result from this
last helper reaches `0x11afd30(reload(link+8))`. The outer holder update already
gates `0x116ff00` on holder+0xd6. Therefore index selection is conditional within
a conditional holder path, not an established once-per-physics-step operation.

A second consumer, `0x11a8230`, reads the same current record directly, then
selects a nested 0xa468-byte record from pointer +0x434/count +0x43e. An external
index selects that nested record when in range; otherwise a nonempty collection
falls back to its first record. Modes 0 and 1 test four corresponding pairs of
32-bit fields for kind 1 and IDs 200/208/203/205. Other modes return false. This
is a lead for the meaning of these contexts; the ID-to-physical-control mapping
has not been established. Empty nested collections can lead to null accesses in
modes 0/1, so this is not a safe public query interface yet.

The [static evidence receipt](../../native/snow_host/input_cache_index_writer_evidence.json)
records inspected spans and direct call sites. No original-routine execution,
live observation, external-query semantics, or callback effects are validated by
this receipt. Next: resolve the query target/import, trace range/flag writers,
and decode the post-assignment helper before implementing a complete mutable
cache-selection service. Existing stable-snapshot selectors remain valid within
their stated assumptions.


### Executable selection decision

[`choose_input_cache`](../../engine/action_cache_policy.py) exposes the writer's
selection decision with explicit scan bounds, fallback flag, active count,
record IDs and a query callback. It returns the selected index, the indices
queried in order, and whether the zero-fallback notifications are requested.
It does not assign native memory or execute the unresolved post-selection and
notification helpers. Inputs have no established physical units; these are
indices, flags, IDs and opaque uint32 query results. Call cadence is explicit
and caller-owned. Snapshot stability is required.

A caller can inspect a synthetic decision without a game or binary:

```python
from engine.action_cache_policy import choose_input_cache

result = choose_input_cache(
    scan_begin=0, scan_end=3, fallback_flag=1, record_count=4,
    record_ids=(8, 9, 10), query=lambda ident: 0 if ident == 9 else 1,
)
# selected_index=1, queried_indices=(0, 1), final_notifications=False
```

Missing scanned records and invalid integer inputs raise ValueError. The
original scan can dereference beyond active count; the portable API allows
explicit records outside that count but rejects unavailable storage. It does
not silently clamp scan bounds or treat an invalid zero-result candidate as a
request to keep searching. A query callback exception propagates; already
performed caller-supplied query effects are not rolled back.

The [decision validation receipt](../../native/snow_host/input_cache_policy_validation.json)
compares 1,728 original-writer executions against the portable decision, across
empty and reversed scan ranges, first-zero positions, active count boundaries,
nonzero fallback flag bit patterns, and unchanged/changed old indices. Query
argument order, selected-index stores and notification arguments/order match.
External query results are supplied, the post-selection helper is a no-op, and
notification helpers only record their calls. This validates the writer's
control flow under those explicit substitutions, not the unknown helpers or a
complete mutable service. In particular, callback mutation of the current index
or metadata is not covered. The import table inspected in this pass does not
establish a named import binding for the query target.
