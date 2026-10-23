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


## Record categories and counter producers

The field previously named `fallback_flag_840` is a uint32 **counter**. The
selection API retains its `fallback_flag` keyword for compatibility with the
first implementation, but callers should supply the counter value. Selection
only tests whether it is nonzero. This correction changes the interpretation,
not the previously validated branch results.

The constructor `0x1188f50` initializes current index +0x828 and all four
counters +0x838/+0x83c/+0x840/+0x844 to zero. It calls record insertion
`0x118da80` four times, passing kind 8 and identifiers 0, 1, 2, 3. The insertion
stores kind at record+8 and initializes query ID +0x420 to 0xffffffff. Its
counter branch then applies this policy, with uint32 wrap on every increment:

```text
if kind == 0:
    scan_begin += 1
    scan_end += 1
elif kind in {2, 6, 7, 8, 10}:
    scan_end += 1
    query_id = zero_extend_u16(supplied_record_id)
else:
    fallback_count += 1
    if kind == 9:
        kind9_count += 1
```

The membership test is an unsigned kind<=10 check followed by a bit test of
0x5c4. Large kinds must not alias lower bits through a masked shift. The record
is appended after this classification; the same insertion routine also builds
nested 0xa468-byte configuration records. Those builders remain outside this
kernel. The counter branch does not sort records, so a contiguous category
layout still requires tracing insertion callers and later reordering.

The constructor's four insertions yield scan_begin=0, scan_end=4,
fallback_count=0 and kind9_count=0, with query IDs 0..3, assuming successful
construction. This is consistent with four controller slots, but neither the
kind name nor the external query binding is proved. Do not turn that inference
into a device API contract.

[`count_inserted_cache`](../../engine/action_cache_counts.py) reconstructs the
counter updates and query ID independently of allocation. Inputs and outputs
are integer metadata, not physical quantities. It owns no persistent state;
the caller supplies counters and invokes it once for each intended insertion.
The [counter validation receipt](../../native/snow_host/input_cache_counts_validation.json)
records 272 executions of the original counter instruction slice with no
substituted calls. All four counters and the query ID match, including uint32
wrap, uint16 ID boundaries, kind 9 and large unsigned kinds. This is not a
complete original-constructor or insertion-routine test.

### Cleanup before the selection scan

The earlier final-holder helper calls `0x11ada50` before invoking the external
virtual operation and eventually the selection writer. That cleanup visits
records backward from count-1 while index>=scan_end. For each visited record it
appends a 16-byte entry containing the record's cache pointer and value 5 to the
collection at object+0x848, destroys/removes the record through helpers, and
decrements record count and fallback_count. The entry's final four bytes are
not assigned by this local sequence, so they should not be invented as zero.
The general removal path can copy the last record into the removed slot.
Destructor, allocation and downstream queue behavior are not yet reconstructed.

After removals, cleanup visits records [0, scan_end), changes every nonzero kind
to 8, clears kind9_count, writes 2 at object+0x854, and clears a global dword.
Thus record kinds are mutable and kind9_count is explicitly reset. For a valid
contiguous layout whose trailing length equals fallback_count, cleanup removes
that trailing category before subsequent operations may repopulate it. This is
a conditional interpretation, not proof of the layout invariant or the virtual
operation's effects.

The original backward loop computes count-1 in uint32 and has no local empty
count guard before the unsigned comparison. Count zero is not a proved safe
entry state for this routine. A portable cleanup service must wait for its
preconditions, allocation/destruction effects and deferred-entry consumer to be
resolved. Next leads are insertion callers, the record-copy/removal helpers,
and the virtual operation between cleanup and selection.


## Saved-name restoration before fallback

The helper previously left opaque at `0x1174150` searches for the saved record
name before the fallback selection policy runs. The final-holder helper had
saved current record+0x0c into link+0x78, then called `0x11b0160(root, 0)` before
cleanup. That setter checks index<count, writes current index, calls the same
unresolved post-selection helper, reloads current index and conditionally
notifies old/new change. It is not merely a reset of unrelated metadata.

After cleanup and the virtual enumeration operation, saved-name restoration is:

```text
if saved_name[0] == NUL:
    return false
count = root.record_count
for index in [0, count):
    record = lookup(reload(link.root), index)
    if equal_u16_through_NUL(saved_name, record.name_at_0c):
        if low_byte(record.cache.virtual_120()) != 0:
            set_current_index(reload(link.root), index)
            return true
return false
```

Names match exactly as UTF-16 code units, without case folding, Unicode
normalization, or interpretation of surrogate pairs. Readiness is called only
for matching names. Duplicate names continue searching if an earlier matching
record returns zero in its low byte. Empty saved names bypass all record reads.
A successful match suppresses the fallback scan at `0x11afd30`. Success means
the setter was called, not proof that unresolved callbacks retained the chosen
index. The native search snapshots count but reloads the root per lookup;
concurrent metadata changes can invalidate that count.

[`preferred_input_cache`](../../engine/action_cache_preference.py) implements
the stable-input decision with explicit NUL-terminated UTF-16LE byte storage and
a readiness callback. It returns an index or None and performs no native writes.
The caller decides when to run it. The API rejects missing terminators instead
of reading unbounded memory. It ignores bytes after the first aligned NUL and
preserves lone-surrogate code units.

The [preference receipt](../../native/snow_host/input_cache_preference_validation.json)
compares 80 original search/lookup/setter executions, supplying readiness returns
and a no-op post-selection helper. Exact matching, duplicate handling, callback
order, low-byte booleans and selected-index writes match. The global notification
holder is null in these cases. Readiness meaning and callback mutation remain
unvalidated.

## Enumeration callback and record refresh

The callback passed to virtual +0x20 is `0x115a650`. It accepts a descriptor and
the link context. A mode global gates processing: mode 2 proceeds, mode 1 accepts
descriptor type byte 0x15/0x18 or a successful helper predicate, and other modes
skip. It opens a descriptor through virtual +0x18 and skips on signed failure.
A property query through virtual +0x28 provides a pair of uint16 IDs. Helper
`0x116ac90` queries another property, formats the literal UTF-16 prefix
`\\?\hid#vid_%04x&pid_%04x&ig_`, and compares the queried path against that
prefix. This is concrete device-path evidence; the exact external API binding
and comparison helper semantics remain to be verified.

When that predicate succeeds, a branch table chooses kinds from the ID pair:

| First ID | Second ID | Kind |
| --- | --- | --- |
| 0x28de | any | 7 |
| 0x045e | 0x02d1 | 6 |
| 0x045e | 0x028e or 0x02a1 | 2 |
| 0x046d | 0x1000 | 10 |
| other matched pairs | other | 8 |

The first-ID 0x28de branch can additionally allocate/append a kind-9 record when
two external gates succeed. Their meanings remain unresolved. The selected
kind then goes to `0x11b9320` with descriptor+0x230 as a string source. This helper
uses cursor object+0x858, updates the current record's kind unless it is zero,
optionally copies the string to record+0x214 with size argument 0x104, and
increments the cursor. A zero-kind record returns without advancing the cursor.
There is no local cursor/count check. The final-holder helper explicitly zeros
this cursor before enumeration.

When the path predicate fails, the callback constructs another cache object and
initializes it. On success it derives the appended kind from that object's
+0x820 field: values 1..4 map to 3, value 9 to 4, value 10 to 5, and other values
retain default kind 1. It appends via `0x118da80`, which updates the counters
already reconstructed. Thus enumeration can relabel existing records and append
new records after cleanup. The full ordering invariant is still unproved.

After either route, the callback checks the packed ID pair against two link-local
collections. Kind 7 skips these duplicate checks. If not filtered out, it appends
an eight-byte tuple containing the IDs and kind to a third collection and writes
1 to the global holder's +0xd6 byte. It returns 1 even on skipped/failure paths.
This write is distinct from the outer holder's initial d5-to-d6 copy; treating d6
as immutable throughout the update would be incorrect.

Together these paths explain a device-enumeration and preferred-record refresh
cycle more strongly than a frame-history interpretation. They do not establish
physical button mappings, exact input ingestion time relative to physics, or
thread safety. Next: resolve virtual readiness +0x120 for each cache type and
the external query/post-selection helper, then validate the complete refresh
cycle when live access is available.

The [refresh evidence receipt](../../native/snow_host/input_cache_refresh_evidence.json)
records static spans for this callback, path predicate and related helpers.


## Cache-type readiness callbacks

Constructor vtable assignments now identify virtual +0x120 for three concrete
cache types and the root container. These names describe our interfaces, not
original class names. A record's mutable kind is not sufficient to identify its
implementation; use the actual cache vtable.

| Constructor/table evidence | +0x120 target | Recovered rule |
| --- | --- | --- |
| Four initial caches, table 0x28eff08 | 0x11a7b20 | External query of cache+0x244 slot returns zero |
| Alternate cache constructor 0x1188e80, table 0x28efbe0 | 0x11a7b00 | Byte +0x240 nonzero OR pointer +0x828 non-null |
| Kind-9 construction path, table 0x28f00e8 | 0x11a7af0 | Pointer +0x8b8 non-null |
| Root table 0x28efd70 | 0x11a7ac0 | Delegate to current record cache's virtual +0x120 |

The queried callback reads its uint32 slot from cache+0x244, zeros a 16-byte
stack buffer, passes slot and buffer to `0x1c34f3c`, and returns whether the
32-bit result equals zero. Buffer contents are not used afterward. This is the
same query target used by the fallback scan with record+0x420. The constructor
supplies the same 0..3 slot values to its four initial caches and records.
The callback and fallback policy therefore share a concrete query mechanism;
its external implementation and live state remain unresolved.

The alternate callback short-circuits on the override byte, so its pointer need
not be read in that branch. Neither pointer-based predicate dereferences the
pointer or proves that the device is functioning. The root reads current index
and record pointer without a count check and tail-dispatches to the selected
cache. Its result is the selected cache's result, not a separately cached flag.

[`action_cache_readiness`](../../engine/action_cache_readiness.py) exposes these
three leaf predicates. The queried form accepts an explicit query callback and
creates a fresh zeroed bytearray for its scratch buffer. It discards buffer
writes and tests the entire uint32 status for zero. For example, status 256 is
false here even though saved-name restoration subsequently tests only the low
byte of the resulting boolean. Pointer identities, override bytes and slots are
caller-supplied metadata with no physical units. These APIs perform no device
acquisition or polling on their own and make no update-cadence assumption.

The [readiness receipt](../../native/snow_host/input_cache_readiness_validation.json)
compares 864 original executions directly and through root delegation. It checks
constructor-derived vtable entries, boolean results, query argument values and
the zero-initialized scratch buffer. Only the external slot query is supplied;
it writes synthetic bytes and returns an explicit status. The pointer-based
callbacks and root dispatch execute without substituted calls. Valid stable
indices/records are supplied; invalid metadata and object lifetime are outside
this validation. Twenty focused public tests cover the cache kernels, including
composing readiness with preferred-name selection.

This resolves the local readiness rules for these identified types. It does not
resolve all cache subclasses, the post-selection helper, or the external slot
query. The next useful join is between these device caches and action-source
queries, with scheduler placement kept separate from device-refresh behavior.


## Selected-device publication into the root

The root table's virtual +0x110 resolves to `0x11bb2a0`. This is the update called
at the beginning of the holder cycle, before the separate keyboard/packet
service polling described earlier. It performs device updates and arbitration,
then publishes selected-cache fields into the root. This establishes local
holder ordering, not its position relative to physics substeps.

After arbitration and before derived-state helpers, the original copies:

```text
root.previous_buttons[32] = root.current_buttons[32]
root.current_buttons[32] = selected.current_buttons[32]
root.vectors[2][4] = selected.vectors[2][4]
root.scalars[32] = selected.scalars[32]
```

The raw fields are previous buttons +0x10, current buttons +0x30, vectors +0x1f0
and +0x200, and scalar array +0x168. These are the same vector/scalar offsets
already read by the reconstructed action source. The copy uses raw moves; it
does not normalize, clamp, rescale or interpolate values. It then calls
`0x11798d0(root)` and tail-calls `0x1179d80(root)`. The first starts by moving
+0x7c8 to +0x7d0, clearing +0x7c8 and reading the published vector lanes. The
second advances +0x50/+0x58 timestamps and stamps ordinary button rising edges
into +0x60. Their full bodies remain separate reconstruction work.

[`publish_selected_cache`](../../engine/action_cache_publication.py) implements
only the detached raw-copy stage. It leaves timestamps and derived button fields
unchanged for those later producers. The original reloads current index and the
record pointer separately for button, vector and scalar copies, so concurrent
changes could mix sources; the API explicitly requires stable inputs.

The same module's `reset_input_cache` reconstructs full helper `0x1171c10`, which
these concrete cache types expose at virtual +0x118. It zeros exactly the ranges
[0x10,0x1e8), [0x1f0,0x210), and [0x7c8,0x818), preserving all other bytes. These
are also the exchange helper's ranges. Root virtual +0x118 delegates to the
selected cache's reset; it does not directly reset the root snapshot. Do not
confuse this full reset with helper `0x1171cc0` used on an inactive update branch;
that helper needs its own complete comparison.

The [publication receipt](../../native/snow_host/input_cache_publication_validation.json)
compares every cache byte in 256 original publication-slice cases and 256 complete
full-reset cases without substituted calls. Publication includes 64 cases where
selected cache and root are the same native object. Random raw bytes include
non-finite float encodings without interpreting them as numbers. Disjoint source
bytes remain unchanged. This validates the copy/reset stages, not the complete
root update, device polling, callback effects or downstream timestamps.

### Activity-driven device arbitration

The inspected root update calls helpers `0x116dbe0` and `0x11bda50`, saves the
current index as candidate, obtains a timestamp, and reads an external gate.
When its global signed mode is positive and the gate is true, it iterates records
from scan_begin to count. For each non-null cache it chooses a nested configuration
using an external index, falling back to entry zero if that index is out of range
and the nested collection is nonempty. It calls cache virtual +0x90 with that
configuration pointer, or null for an empty collection.

Activity is considered for all records when the switching byte is nonzero,
otherwise only for the initially selected candidate. A cache is active if any of
its 32 current button bytes is nonzero, or either four-lane vector has a lane
that fails abs(value)<=float32(0.3). All four lanes are tested, including W.
NaNs fail the ordered comparison and therefore count as activity in this local
branch. The constant has bits 0x3e99999a. This is a device-activity threshold,
not evidence of a steering deadzone.

The arbitration additionally requires the earlier timestamp to exceed a global
uint64 read through `0x11653b0`. For each qualifying record:

```text
if not current_record_already_seen_active:
    candidate = index
    current_record_already_seen_active = (index == root.current_index)
any_qualifying_activity = true
notify_helper_1174880(global_holder, 0)
```

With stable selection, the active current record wins when encountered. If it
never qualifies, the last qualifying record wins. Notification still occurs for
later qualifying records after the candidate becomes fixed. Following the loop,
helper `0x11bc980` runs. Selection is changed only if switching remains enabled,
activity occurred, candidate differs from current, and candidate<count. The
same unresolved post-selection helper and old/new notification follow the store.
The publication copy then reads the resulting selected cache.

The non-polling branch conditionally clears caches via `0x1171cc0` depending on
mode and gate changes. Global modes, the gate's meaning, external configuration
selection, and helper effects are unresolved. This arbitration is statically
inspected pseudocode; the publication receipt does not execute or validate it.
Next: virtual +0x90 implementations and the derived-state/timestamp producers,
then a composed root-update validation with explicitly supplied external inputs.


## Root-cache edge timestamps

Helper `0x1179d80`, tail-called after root publication and derived-button
production, advances one pair of clock fields and stamps rising edges. It does
not copy current inputs to previous inputs; those copies belong to earlier
stages. Its complete local behavior is:

```text
previous_clock = current_clock
current_clock = read_timer_once()
for i in 0..31:
    if current_buttons[i] != 0 and previous_buttons[i] == 0:
        ordinary_press_stamp[i] = current_clock
for i in 0..7:
    if current_derived[i] != 0 and previous_derived[i] == 0:
        derived_press_stamp[i] = current_clock
```

Clock fields are uint64 +0x50/+0x58. Ordinary current/previous bytes are +0x30/
+0x10, with stamps at +0x60. Derived current/previous bytes are +0x7c8/+0x7d0,
with stamps at +0x7d8. Every nonzero byte counts as active; this is not a high-bit
test. A held value changing from 1 to 255 keeps its old stamp. Release also
keeps the stamp. A later zero-to-nonzero transition replaces it with the newly
read clock, even if that value is numerically smaller. No monotonicity check,
subtraction, wrap correction, duration or physical-unit conversion occurs here.

[`stamp_input_cache`](../../engine/action_cache_timestamps.py) accepts an exact
raw cache snapshot and an explicit uint64 time, preserving all unrelated bytes.
It composes after `publish_selected_cache` for ordinary buttons. Complete native
order also runs the derived-button producer between publication and stamping;
callers must supply those current/previous derived bytes until that producer is
reconstructed. Repeated stamping without updating previous inputs can repeatedly
stamp the same apparent edge, so this helper alone is not an input-step loop.

This is distinct from `refresh_button_timestamps`, which operates on the separate
256-key/20-byte service cache and two clock sources. The root has 32 ordinary and
eight derived byte inputs and only one clock read. It has no packet-sign edge
slots or secondary clock array. Shared zero-to-nonzero behavior does not justify
combining these layouts or their update order.

The [root timestamp receipt](../../native/snow_host/input_cache_timestamps_validation.json)
compares 512 complete original-helper executions, supplying only the timer return.
Every byte of the 0x818-byte cache span matches, and the timer is called exactly
once per invocation. Tests include noncanonical nonzero bytes, held/released
states, zero time, full uint64 time and unrelated raw data preservation. Public
sequence tests compose publication and stamping across press, held-value change,
release and repress, checking both edge stamps and previous-clock transfer.
The derived-input producer, timer units and scheduler cadence remain unresolved.


## Derived directional inputs

Helper `0x11798d0` converts each published vector's X/Y pair into at most one
active derived byte. It first copies all eight current derived bytes at +0x7c8
to previous at +0x7d0 and clears current. For each pair, its rule is:

```text
if abs(x) > float32(0.3) or abs(y) > float32(0.3):
    if abs(x) > abs(y):
        direction = positive_X if x > 0 else negative_X
    else:
        direction = positive_Y if y > 0 else negative_Y
    current_derived[vector_index * 4 + direction] = 1
```

Direction indices are negative Y=0, negative X=1, positive Y=2, positive X=3.
The first four bytes correspond to vector +0x1f0; the next four to +0x200. Only X
and Y participate. Z and W do not affect this helper. Threshold equality stays
inactive, and equal active magnitudes select Y. There is no hysteresis or
normalization. These bytes encode digital directions alongside unchanged analog
values; this does not establish a deadzone in the analog steering path. Physical
axis meanings such as left/right/up/down require the device mapping.

The constant is float32 bits 0x3e99999a. The original converts components to
double, clears their double sign bits, then converts back before comparisons.
For ordinary float32 values this gives exact magnitude. Unordered comparisons
are significant: if X exceeds threshold but Y is NaN, the axis comparison falls
to Y, whose positive comparison fails, producing the negative-Y byte. If X is
NaN and Y is inactive, neither ordered threshold comparison passes and no byte
is set. Floating-point exception flags/traps are outside the portable model.

[`derive_input_directions`](../../engine/action_cache_directions.py) implements
this byte production on raw cache snapshots. Its companion
`publish_derived_and_stamp(root, selected, now)` composes the now-reconstructed
tail in the original order: selected-cache publication, direction generation,
then edge stamping. Inputs are detached stable snapshots and an explicit opaque
uint64 timer value. The result preserves unrelated bytes and the caller's raw
analog encodings. It does not choose a device, invoke device polling, modify a
live process, or decide scheduler cadence.

A direction held over several updates retains its press timestamp. A switch
from positive X to positive Y releases the X byte and stamps the new Y byte;
returning to X stamps X again. The source analog vector is still available
unchanged throughout. Ordinary button history comes from publication, while
derived history comes from this helper.

The [composed-tail receipt](../../native/snow_host/input_cache_directions_validation.json)
compares 737 cases against the original publication slice followed by complete
direction and timestamp helpers in native order. Every byte matches after
direction generation and again after stamping. The validator sequences these
original segments; it does not execute the complete root callback. Only the
timer wrapper is supplied. Inputs include float32 threshold neighbors, signed
zeros, diagonal ties, infinities, quiet/signaling NaNs and random raw encodings.
Public tests include repeated directions and direction changes through the
composed API. Exception flags and traps are not compared.

This closes the previously missing derived-input stage in the publication and
root timestamp sections. Remaining upstream work is device virtual +0x90
production, arbitration gates and source-query consumption. Scheduling relative
to physics remains a separate unresolved join.


## Initial-slot packet conversion

The four initial caches use virtual +0x90 target `0x11bd1c0`. It reads slot
+0x244 through the same external query seen in readiness/fallback selection.
The successful query supplies a 16-byte packet. The numeric consumers establish
this local packet layout, without requiring an assumed external API name:

| Packet bytes | Use |
| --- | --- |
| 0..3 | Not consumed by the conversion kernels below |
| 4..5 | uint16 button bits |
| 6, 7 | Two uint8 analog trigger values |
| 8..15 | Four little-endian signed int16 axes |

Axis conversion stores float32(axis/32767) into cache +0x1f0, +0x1f4, +0x200,
and +0x204. It does not write Z/W, clamp, apply a deadzone, or combine axes.
The value -32768 therefore produces approximately -1.0000305, whereas +32767
produces exactly +1. Later processing may still alter these channels.

When the supplied configuration pointer is non-null, helper `0x11bc880` maps
32 configuration records of stride 0x41c. It reads kind at record+4 and code at
record+8. For each output byte/scalar pair:

```text
if kind != 1 or code == 0:
    pressed = 0
    scalar = 0.0
else:
    mask = uint32(1 << ((code - 1) & 31))
    if mask == 0x400 or mask == 0x800:
        raw = packet[6 if mask == 0x400 else 7]
        pressed = raw > 30
        scalar = float32(raw / 255)
    else:
        pressed = (packet.button_bits & mask) == mask
        scalar = 1.0 if pressed else 0.0
```

The x86 shift masks its count to five bits. Thus code 33 aliases code 1, and
code 43 aliases trigger code 11. Values selecting bits 16..31 cannot be present
in the uint16 packet button field. An unmapped output is explicitly cleared.
Trigger analog values remain nonzero below the digital threshold; the digital
comparison is strict, so 30 is false and 31 is true. These configuration codes
are not semantic gameplay action names.

[`action_slot_packet`](../../engine/action_slot_packet.py) exposes axis decoding
and button mapping separately on detached snapshots, so a null native mapping
configuration is not silently replaced by an invented default. Callers supply
packet bytes and all 32 mapping pairs. These normalized values are dimensionless;
no elapsed time or scheduling is involved in either conversion. The
[packet receipt](../../native/snow_host/input_slot_packet_validation.json)
compares 512 original axis-slice cases and 512 complete mapper cases without
substituted calls. All cache bytes and float32 bits match across axis extrema,
trigger threshold boundaries, shift wrapping and disabled mappings.

### Query and connection-state gates

Before querying, the callback calls common helper `0x1178910`, then copies its
current buttons to previous. If global holder+0xd6 is zero and its cached
query-success byte +0x834 is also zero, it calls virtual reset +0x118 and returns
without polling. Otherwise it calls the slot query once and records:

```text
new_success = (query_status == 0)
byte_834 = new_success
byte_836 = old_success and not new_success
byte_835 = not old_success and new_success
```

Failure resets the cache and returns. A new success zeros 24 bytes at +0x820,
sets +0x834/+0x835 to 1, and calls another unresolved external helper with slot,
value 1, and that buffer. A continuing success skips this initialization. The
query's stack output is not initialized by this caller before the query; only
the successful path consumes it. A portable polling implementation must not
invent failed-query packet contents.

After conversion and optional mapping, the callback prepares an output pair
through gated arithmetic or zeros, calls another external helper, then calls
`0x1173da0`, derived-direction generation and edge stamping. The output helper
and `0x1173da0` remain unresolved, as do common-helper effects. Consequently the
packet kernels establish an upstream producer, but concatenating them directly
with the published tail does not yet prove complete original device-update
behavior. Next: decode `0x1173da0` and the common helper before a full composed
initial-slot update. Live scheduler placement remains separate.


## Analog radial deadzone and magnitude limit

Post-mapping helper `0x1173da0` shapes both four-lane vectors using the same
float32 deadzone from cache+0x210. This resolves a later stage explicitly left
open in the packet conversion section: raw axes are unclamped at conversion,
but the subsequent vector stage can zero, rescale or normalize them.

Let v=(x,y,z,w), d be the supplied deadzone, and f denote float32 rounding.
The original squared-length reduction is:

```text
s[i] = f(v[i] * v[i])
q = f(f(s[0] + s[2]) + f(s[1] + s[3]))
if f(d*d) > q:
    output = (0, 0, 0, 0)
elif q > 1:
    r = SIMD_reciprocal_sqrt_estimate(q)
    factor = f(f(3 - f(f(r*q)*r)) * f(0.5*r))
    output[i] = f(factor * v[i])
elif d > 0 and d < 1:
    length = f(sqrt(q))
    scale = f(f(f(length-d) / f(1-d)) / length)
    output[i] = f(scale * v[i])
else:
    output = v
```

All four lanes participate, unlike derived digital directions, which inspect
only XY. No lane is silently cleared here. The first branch precedes magnitude
limiting, so an unusually large or negative deadzone still affects its squared
comparison. Deadzone is not clamped. For ordinary 0<d<1, values inside the
radius are zeroed; the interval from d to 1 is rescaled to magnitude 0..1; values
above magnitude 1 are approximately normalized. Equality at the deadzone reaches
the remapping branch and produces zero for ordinary finite cases. There is no
history, elapsed time or smoothing state in this helper.

[`shape_slot_vector` and `shape_slot_cache`](../../engine/action_slot_deadzone.py)
implement this local arithmetic with explicit finite inputs. The cache adapter
reads d at +0x210 and changes only the vectors at +0x1f0/+0x200. Its default
reciprocal-square-root seed is rounded 1/sqrt(q), a numerical substitute. The
API accepts an explicit `rsqrt_estimate` callback for matching a target SIMD seed.
The Newton refinement and subsequent operations retain float32 rounding order.
No original SIMD bit-equivalence claim applies to the default seed.

Nonfinite inputs/intermediates, overflow and a zero divisor produced by
underflow are rejected. In particular, a tiny positive d can have f(d*d)==0;
with a zero vector, the native remapping branch can reach division by zero.
The portable finite model reports that boundary instead of silently inventing
an output. Processor floating-point flags and traps are not modeled.

The [deadzone receipt](../../native/snow_host/input_slot_deadzone_validation.json)
compares 945 complete original-helper executions and all cache bytes. The
comparison supplies observed original RSQRT seeds for 1,580 normalization
vectors; no native calls are substituted. Cases include zero vectors, deadzone
equality, ordinary remapping, magnitude limiting, nonzero W, negative/large
deadzones and randomized finite lanes. The public tests separately check the
explicit underflow rejection. These results establish local arithmetic, not
active player tuning, all exceptional inputs, or the full polling callback.

The known initial-slot success path is now packet axes -> optional configured
button/trigger mapping -> radial shaping -> derived directions -> edge stamps,
with additional unresolved output/common-helper effects around those stages.
The root later copies the selected cache and regenerates directions/stamps using
its own history. Do not collapse device and root histories into one cache.
Next: trace the deadzone writer and common helper to establish actual defaults
and remaining side effects before composing a complete device update.


## Deadzone default and propagation setter

The common cache constructor `0x114ef10` calls the full cache reset and then
stores float32 bits 0x3e99999a at +0x210: the constructor deadzone is 0.3f. The
reset excludes this field, so subsequent resets preserve the configured value.
This default is a static constructor finding, not a live gameplay measurement.

Leaf setter `0x1174d40` copies the low float32 bits of its second argument to
+0x210 and returns. It performs no comparison, clamp or normalization. The three
identified concrete cache tables expose it at virtual +0x100. The root table's
corresponding slot targets `0x11b8880`, which does:

```text
set_leaf_deadzone(root, value)
begin = root.records
end = begin + root.record_count * 0x440
for record in [begin, end):
    record.cache.virtual_100(value)
```

Root update happens first, then every record in storage order, including aliases.
The record span is captured before iteration. Each record's cache pointer is read
when visited. No null guard, deduplication, lock, rollback or notification is
present here. Different virtual implementations could have other effects; the
identified leaf types simply store the bits. Mutating/reallocating the record
array during the callbacks is not proved safe.

The raw [`set_cache_deadzone_bits`](../../engine/action_slot_deadzone.py) API
mirrors the leaf store on a detached snapshot, preserving all encodings including
NaNs, infinities and signed zero. It intentionally differs from the finite
shaping API, which rejects unsupported numerical cases. The exported
`DEFAULT_DEADZONE_BITS` names the constructor value; no runtime inspector or
simulation silently substitutes it for unknown active tuning.

The [setter receipt](../../native/snow_host/input_deadzone_setter_validation.json)
compares 384 complete original root-setter executions through the concrete leaf
virtual methods without substitutions. Root and child bytes, root-first call
order, empty record arrays, repeated child identities and raw float32 encodings
match. The constructor store is statically inspected separately; the complete
constructor is not executed by this receipt.

A derived implication of the two shaping stages is useful for experiments. For
a single active axis, deadzone d=0.3 and analog magnitude at most one, the radial
output is (m-d)/(1-d). The later digital-direction threshold of 0.3 therefore
corresponds approximately to raw magnitude m>0.51, with float32 rounding at the
boundary. This is a conditional calculation, not an additional stored threshold
or a claim about the player's active setting. Both stages must be included when
comparing raw input to digital events.

Next: identify the caller of virtual +0x100 and its configuration source. The
constructor default, raw setter and propagation path are established; active
tuning, safe live invocation context and physical-action mapping remain open.


## Setup-time deadzone override

A concrete caller now supersedes any interpretation of constructor 0.3f as a
universal setting. Setup routine `0x47c330` accepts a uint32 offset as its second
argument, builds an adapter at owner+8, and eventually calls helper `0x981ad0`
with that offset. It then loads constant float32 0.25 from `0x1df4050` and invokes
virtual +0x100 on the adapter's resolved cache pointer.

The adapter helper stores the supplied offset at adapter+8, gets the global
holder, calls generic selector `0x11639a0(holder, offset)`, and stores the selected
cache pointer at adapter+0. This generic selector implements the same arithmetic
as the previously reconstructed holder-field selectors:

```text
if offset == 0:
    selected = holder.link.root
else:
    selected = root.records[wrap_u32(root.current_index + offset) % count].cache
adapter.offset = offset
adapter.cache = selected
selected.virtual_set_deadzone(0.25f)
```

The actual helper writes adapter.offset before selection. A selection failure
therefore does not imply an untouched adapter. The pseudocode above assumes
valid stable metadata; native root/count reload hazards remain as documented
for the other selectors.

Offset zero resolves the root and calls its propagation setter, changing the
root and every concrete record cache to 0.25f. A nonzero offset resolves one
record cache and invokes its setter, ordinarily changing that cache alone. The
constructor default and this later override are both recovered facts. Which
setup instance belongs to the active player, the supplied offset in gameplay,
and any later overrides remain unverified. No global engine default is changed
in the portable model on the strength of this caller alone.

The [setup validation receipt](../../native/snow_host/input_deadzone_setup_validation.json)
executes the original setup tail, adapter helper, generic selector and concrete
virtual setters for 45 synthetic object graphs without substituted calls.
Counts 1/3/5, zero/nonzero offsets and uint32 wrap cases match adapter identity,
stored offset and every root/child cache byte. The earlier allocator and setup
body are excluded; this is not a full constructor or live-player test.

For the conditional single-axis experiment described above, d=0.25 makes the
later digital threshold approximately raw magnitude >0.475, rather than the
>0.51 derived for d=0.3. This demonstrates why configuration provenance matters:
using the constructor value alone changes predicted input timing. These figures
are derived real-arithmetic approximations with float32 boundary effects, not
additional binary constants or observed physical-controller thresholds.

The caller search found no direct call to the root propagation implementation
in the decoded function ranges; the successful route is virtual dispatch.
Other uses of virtual slot +0x100 belong to unrelated interfaces. Matching a slot
number alone is not sufficient to attribute a deadzone write. Next: identify
setup routine callers and their offset values, then verify the corresponding
adapter during an authorized live session.


## Four-adapter setup and holder selection link

The decoded direct caller of setup routine `0x47c330` is `0x47d650`. It creates
four owner objects in a loop with explicit offsets 0, 1, 2 and 3. Each iteration
allocates an object, calls constructor `0x4413a0`, runs setup(owner, offset),
then calls `0x47cd00(owner)` and stores the owner in its four-entry array.
This is no longer an unknown offset at this call site.

Before the loop, the caller copies global holder+0x230 into manager+0x50. After
each object's setup, it clears owner byte +0x10 when the loop offset differs
from that saved value. Matching offsets leave the byte unchanged. The owner
constructor initializes this byte to 1, but callback effects between construction
and this comparison have not all been audited; the precise pseudocode therefore
preserves the distinction between leaving unchanged and forcing true:

```text
selected_offset = global_holder.uint32_at_230
manager.saved_offset = selected_offset
manager.array_count = 4
for offset in 0..3:
    owner = allocate_and_construct()
    setup(owner, offset)             # includes deadzone 0.25f
    helper_47cd00(owner)             # further action/configuration setup
    manager.owners[offset] = owner
    if offset != selected_offset:
        owner.byte_10 = 0
```

This holder field is already used by selector `0x115dd60`, one of the pair that
brackets the holder update with cache exchanges. The connection establishes
shared selection metadata across setup and update. It does not identify a
specific player's adapter or prove the scheduling phase that invokes this setup.
If selected_offset is outside 0..3, the explicit comparison clears all four
bytes; there is no fallback assignment in this loop.

Under valid stable metadata, offset 0 selects the root, so the first setup call
propagates 0.25f to every current device cache. The remaining offsets select
individual caches using current-index-relative modulo arithmetic and set them
to the same value. Small record counts can alias targets; they do not turn these
arguments into fixed physical device indices. The state of caches inserted after
this sequence is a separate question: their common constructor still starts at
0.3f unless another path changes them. Do not infer perpetual global 0.25f.

The parent routine surrounds its work with a lock-like protocol involving thread
identity, recursive depth and atomic bitfield operations, then calls another
registration helper. That local protocol is not a license to call the nested
setter from any thread; its ownership and other participants remain unresolved.
Allocation failure also is not proved recoverable: a null allocation result can
still flow into setup in the inspected branch.

The [four-adapter static receipt](../../native/snow_host/input_adapter_setup_evidence.json)
records the complete caller span, owner constructor initialization, setup call
site and shared-holder field reference. This pass adds static control/data-flow
evidence, not a full allocator/callback execution test. The previous 45-case
setup-tail receipt continues to validate selector/setter behavior for supplied
object graphs. Next: decode `0x47cd00`'s constructed action/configuration objects
and their consumers, then identify the manager's runtime registration/callers.


## Adapter binding slots and source construction

Helper `0x47cd00`, called after each adapter setup, constructs **31** indexed
binding slots, numbered 0..30. These are not the 32 packet-button outputs or the
four device adapters. Each 0x30-byte slot object stores its index at +8, the
shared adapter at +0x10, a reference handle at +0x18, a resolved configuration
pointer at +0x20, and a separately allocated 0x20-byte registry at +0x28. The
registry also stores the shared adapter at +0x10. The slot objects are appended
to owner+0xb4. These sizes/field names describe this allocation path only.

Binding helper `0x47db40` obtains a resource-handle collection through an external
query and scans it in order. It resolves each acquired handle using the reference
state, compares configuration+0x24 with slot.index, and accepts only the first
resolved match in that invocation. It retains that handle in slot+0x18, writes
its resolved pointer at +0x20, and writes a backlink at configuration+0x30 to the
slot. Later matching entries are not selected, although their temporary
references are still released. Handle ownership and collection cleanup use real
atomic reference operations; this is not a read-only lookup.

When the selected handle is non-sentinel, helper `0x47c220` visits the child
handle array at configuration+0x18. It creates each source through
`0x458ae0(adapter, child_handle)` and attempts registry insertion through
`0x4cbd20`. If insertion fails for a non-null source, it invokes the source's
virtual +0x48 cleanup, destructor and allocator release. Therefore an unsuccessful
registration does not imply the source was never created.

### Source factory dispatch

The factory resolves the child handle, then tests six configuration types in
order using helper `0x11a7320`. The first successful test selects a builder:

| Test order | Builder RVA |
| --- | --- |
| 1 | 0x457630 |
| 2 | 0x4575b0 |
| 3 | 0x457890 |
| 4 | 0x457910 |
| 5 | 0x4577a0 |
| 6 | 0x457720 |

Unresolved handles and configurations matching none of these tests return null.
The builder identities are resolved below. Type descriptor names and sport or
semantic control names remain unassigned. These are factory
branches, not a list of six physical devices.

### Registry insertion rules

The registry helper reads a source configuration pointer at source+0x90 and its
uint32 identifier at configuration+0x18. Its local decisions are:

```text
if source == null or source.configuration == null:
    reject
if identifier == 0xeb:
    reject
if identifier in {0x36, 0x37}:
    key = wrap_u32(registry.sequence_counter + 0xea)
    enter_global_guard()
    map_find_or_insert(key).value = source
    leave_global_guard()
    registry.sequence_counter += 1
    accept
else:
    if map_lookup(identifier) exists:
        reject
    map_insert(identifier, source)
    accept
```

The special branch does not perform the ordinary duplicate precheck. Its keys
are generated independently of the incoming ID; replacing a preexisting entry
and the reference effects of map helpers remain to be checked. The precise
guard implementation is unresolved. ID 0xeb rejection applies to the incoming
configuration ID, not to generated keys. No meaning such as jump, brake or
steering is established by these integers alone.

The owner setup also writes a 31-entry uint32 array at +0x14. Its values are 0,
1 and 2, including a qword store that writes adjacent 1 and 0 entries. Their
consumer is not yet decoded, so these are not labeled button states or action
types. The slot list is configuration-driven; reconstructing its semantics
requires the selected resources and factory consumers.

The [binding-route receipt](../../native/snow_host/input_binding_routes_evidence.json)
records inspected spans and factory targets. This pass is static control/data
flow only; allocation, resource resolution, source callbacks and map helpers
were not executed. It connects adapter setup to configuration-driven sources,
without proving that these are the same active sources captured in prior live
motion observations. Next: decode the six builders' constructors and virtual
initializers, join their source types to the existing action-source research,
and recover the owner-array consumer.


## Source builders join the observed action types

The six builders install concrete main virtual tables, then invoke virtual
+0x40 with `(source, adapter, child_handle_reference)`. The table's +0x10 slot
identifies the evaluation callback. Tracing those stores gives:

| Factory order | Builder | Bytes allocated | Main table | Evaluate +0x10 | Initialize +0x40 | Established type |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0x457630 | 0xd0 | 0x1e6b6a0 | 0x4b2370 | 0x47ae20 | Unassigned |
| 2 | 0x4575b0 | 0x100 | 0x1e6b650 | 0x4b21d0 | 0x47ad50 | Vector source |
| 3 | 0x457890 | 0x100 | 0x1e6b790 | 0x4b2900 | 0x47ad50 | Unassigned |
| 4 | 0x457910 | 0xe0 | 0x1e6b7e0 | 0x4b2a20 | 0x47ace0 | Unassigned |
| 5 | 0x4577a0 | 0xd0 | 0x1e6b740 | 0x4b2680 | 0x47ad50 | Directional source |
| 6 | 0x457720 | 0xd0 | 0x1e6b6f0 | 0x4b24c0 | 0x47af10 | Unassigned |

Builders 2, 3 and 6 call constructors 0x441020, 0x441190 and 0x4410f0;
the other constructors are inline. The vector and directional table/callback
pairs exactly match the two children recorded in
[the live composite observation](MOTION_MEMBERSHIP_OBSERVATION.md#live-composite-has-vector-source-and-directional-children).
This establishes a **type-level connection** between adapter configuration and
the observed action pipeline. It does not establish that this factory invocation
created those particular live objects, that the registry owns the player's
currently selected action, or when evaluation runs relative to physics substeps.

### Shared initialization and ownership

Static inspection of initializer 0x47ad50 shows the following sequence for
builders 2, 3 and 5. Field labels below are explanatory names, not an original
class declaration. `resolve` returns the handle's pointer only when the signed
state word at +0x0c is negative; otherwise it returns null.

```text
source.adapter = adapter                         # +0x10
incoming = *child_handle_reference
atomic_increment(incoming.reference_count)       # +8
old = atomic_exchange(source.handle, incoming)   # +0x98
previous_count = atomic_decrement_return_old(old.reference_count)
if previous_count == 1 and (old.state & 0x00ffffff) == 0:
    release_handle(old)
source.configuration = resolve(source.handle)   # +0x90
source.virtual_38()                              # type-specific setup

if source.field_b8 != null:
    nested_handle_reference = &source.field_b8.field_28
    nested_configuration = resolve(*nested_handle_reference)
    result = null
    if nested_configuration != null:
        result = nested_configuration.virtual_98(nested_handle_reference)
    if result == null:
        result = fallback_457ee0(nested_handle_reference)
    source.field_b0 = result
    result.virtual_10(source.adapter)
```

The initializer does not simply copy an adapter pointer: it transfers handle
ownership, resolves configuration, invokes type-specific setup, then optionally
creates and initializes another object. There is no visible null check after
the fallback before its virtual call. The following section resolves virtual
+0x38 for the vector/directional types. The nested object and other three
initialization variants remain open in this construction path. Do not substitute a borrowed pointer assignment for the
reference operations when designing an in-process API.

### Validation and remaining boundary

[Builder validation](../../native/snow_host/input_source_builders_validation.json)
executed all six original successful-allocation paths with three different
initial storage patterns, 18 cases total. It checked allocation size/alignment,
main table identity, evaluation/initialization entries, selected zero-initialized
base fields, initializer argument order, and returned source identity.
Allocator calls supplied storage; helper 0x57f660 and virtual +0x40 were
substituted. Therefore this validates constructor dispatch and arguments, not
resource lifetime, container setup, initialization side effects or source
behavior. Shared initializer pseudocode above remains static evidence.

Next useful join: decode virtual +0x38 for the vector and directional types and
follow the binding registry's consumer. That can connect selected resources to
source configuration without assuming that a matching type proves player
ownership. Exact device-ingestion versus physics-substep order remains separate.

## Vector source configuration and cache reads

Both the vector and directional main tables use virtual +0x38 = 0x4b1580.
That callback resolves source.handle at +0x98 and stores the result at +0xb8.
Consequently +0xb8 is the resolved source configuration in this setup path,
not another runtime source object. Under stable handle state it aliases the
configuration already stored at +0x90. The two resolutions occur separately;
concurrent changes could invalidate that equality. The nested handle used by
the shared initializer is therefore at configuration+0x28.

For the vector source, configuration+0x30 selects acquisition mode and +0x34
selects a lane operation. Helper 0x4b8ca0 first clears all four output lanes:

```text
out = [positive_zero, positive_zero, positive_zero, positive_zero]
if mode in {0, 1}:
    if low_byte(vector_gate(adapter, mode)) == 0:
        out = read_cached_vector(adapter, mode)
elif mode in {2, 3}:
    index = 10 if mode == 2 else 12
    if low_byte(scalar_gate(adapter, index)) == 0:
        out.x = read_cached_scalar(adapter, index)
# Other uint32 modes leave zero and do not query.

# Caller 0x4b21d0 applies this before processor evaluation:
if mode <= 1:  # unsigned comparison
    if lane == 1:
        out.y = positive_zero
    elif lane == 2:
        out.x = out.y
        out.y = positive_zero
# Z and W are preserved. Lane 2 is a copy, not an XY swap.
```

The vector read helper 0x4b8fe0 takes the cache pointer from adapter+0 and reads
16 bytes at cache+0x1f0+16*mode on its permitted path. These are the same two
vectors populated by the packet/deadzone/publication paths above. It inspects
the ownership list under a lock: an empty list or a null final owner permits
the cached read, while a non-null final owner produces zero. The lock is
released before copying the vector, so this is not an atomic snapshot guarantee.
The scalar helper 0x4b8e80 has a direct cache+0x168+4*index read when the owner
list is empty. Its remaining branch and the preceding gate helpers are not
included in this pass's behavioral validation. No physical stick or trigger
names are inferred solely from these mode numbers.

[select_vector_source](../../engine/action_vector_selection.py) exposes this
acquisition/lane stage using explicit gate and reader callbacks. Its values are
raw float32 bytes to preserve exact copy behavior, including signed zero and
NaN payloads. Processor response, normalization and final sample publication
remain subsequent stages. A null source configuration causes the original
source evaluator to skip its update; callers must not replace that behavior
with this helper's zero result for an unsupported mode.

[Validation receipt](../../native/snow_host/input_vector_selection_validation.json):
180 cases execute the original acquisition helper followed by the original
caller lane-selection slice. All output bytes and callback sequences match the
independent model across supported/unsupported modes, lane selections, gate
results and distinct raw payloads. Gate and read callbacks were supplied;
cache locking, ownership arbitration and hardware polling were not executed.
The shared configuration callback and cache-address join are static findings.
