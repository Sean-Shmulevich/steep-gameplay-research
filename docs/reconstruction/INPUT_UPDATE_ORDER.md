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
