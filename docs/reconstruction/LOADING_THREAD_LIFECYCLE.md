# Loading-thread drain and shutdown

## Receiver identity

The constructor installs a table whose loop slot points to a routine carrying the
image label `::Engine::Loading::LoadingThread::ThreadRun`. Its event, notification
word and stop byte match those used by the inspected drain/stop/wake/join routine.
Constructor initialization also matches the cleanup fields read below. This is a
separate object layout from ordinary scheduler workers and the idle-task pool.

The stop routine has no confirmed aligned direct caller or stored function-pointer
reference in the bounded search. Its local behavior is established; runtime
reachability and the outer owner invoking it remain open. The type relationship
does not establish that this stop routine runs during every shutdown.

## What the drain fields mean

One loop phase sets a busy flag, atomically takes and clears a pending count, then
processes that many entries from a protected ring of object pointers. Each nonnull
entry is virtually destroyed and its allocation released. The normal-return path
clears the busy flag. Thus the stop routine's two fields have a concrete resource-
destruction relationship, not a generic engine job-accounting meaning.

```text
process_destruction_batch(thread):
    thread.destruction_busy = 1
    count = atomic_exchange(thread.pending_destructions, 0)
    retained_object = null
    while signed(count) > 0:
        lock(thread.ring_lock)
        if signed(thread.ring_count) > 0:
            retained_object = thread.ring[thread.read_index]
            thread.read_index = signed_remainder(int32(thread.read_index + 1),
                                                 thread.ring_capacity)
            thread.ring_count -= 1
        unlock(thread.ring_lock)
        if retained_object != null:
            metadata = inspect_allocation(retained_object)
            retained_object.destroy_virtual(non_deleting_flag=0)
            release_allocation(retained_object, metadata)
        count -= 1
    thread.destruction_busy = 0
```

The retained pointer is initialized before the loop, not cleared at the start of
every iteration. Correctness therefore depends on the pending count and ring
population staying consistent. The producer below narrows their relationship; we do not
claim this inconsistency occurs in the game. A substitute implementation that
silently returns null from an empty ring would hide this native invariant.

Setting busy precedes the exchange that clears pending. This avoids one obvious
local gap during handoff, but the stop routine reads the fields sequentially. New
submissions and other consumers still require separate exclusion and ordering
proof. The batch fixes its iteration count at the exchange; submissions afterward
are not automatically included in that batch.

## Stop, notification and join

```text
stop_and_join(thread):
    while load(thread.pending_destructions) != 0 or
          load(thread.destruction_busy) != 0:
        yield_adapter(1)
    thread.stop = true
    repeat:
        old = load(thread.notification)
        desired = 1 if signed(old) >= 1 else int32(old + 1)
    until compare_exchange(thread.notification, old, desired)
    if signed(old) < 0:
        notify_adapter(thread.event_holder)
    return explicit_thread_join(thread, all_ones_timeout)
```

This notification cap compares the old value before incrementing. It differs at
extreme overflow inputs from the ordinary worker's increment-then-signed-min
formula. The common explicit join contract is described in
[worker context](WORKER_THREAD_CONTEXT.md#explicit-thread-join-wrapper).
Protected adapter identities and exact timeout/yield units remain unresolved.

The loop checks stop before beginning, then decrements the notification word and
waits if required. After a wait returns, it runs three local processing phases and
another manager callback before checking stop again. Therefore waking it with
stop already set can still permit another processing pass. The destruction batch
is only one of those phases. The other phase workloads remain open.

After the loop, a retained object is cleared and passed to a cleanup helper under
a lock. A separate callback collection is then visited in reverse index order
under another lock. These actions occur before the shared thread entry returns;
the stop flag alone does not prove they have completed.

## Reconstruction boundary

No live shutdown or debugger attachment was performed. This static pass identifies
which objects and counters the sequence concerns. It does not prove global
quiescence, safe asset replacement, exclusion of new loading requests, callback
exception cleanup or valid ring population. The independent engine does not yet
implement a substitute loading pipeline under this recovered name.

The producer follow-up below joins the pending-count and ring writers. The next
missing relationship is the outer shutdown caller. That is more useful than treating these two zero fields as
an engine-wide pause signal.


## Staging and publication producer

The ring insertion helper uses the same lock as the consumer. It tries to grow a
full ring by 1024 entries, then writes an object pointer if capacity exceeds count,
advances the write index with signed remainder, and increments the ring count.
It atomically increments a separate staged count before releasing the lock.
The increment is outside the successful-insertion branch, so allocation/growth
behavior must be known before assuming count conservation on every failure path.

A higher-level caller holds the loading-thread ring lock across a wider operation
and can call this insertion helper. Nested locking behavior is therefore another
platform contract; it must not be replaced with an arbitrary nonrecursive mutex.
The caller either queues an eligible object for deferred destruction or appends
it to a caller-provided collection, depending on its mode. Exact resource-reference
and release eligibility conditions remain outside this focused publication result.

At the end of that operation, while still holding the outer lock, it publishes:

```text
captured = atomic_exchange(thread.staged_destructions, 0)
if captured != 0:
    atomic_fetch_add(thread.pending_destructions, captured)
    notify_loading_thread_with_counter_protocol(thread)
# Other local cleanup follows before releasing the outer ring lock.
```

This is a two-stage handoff. Ring insertion does not immediately increase pending;
the caller later transfers the staged count. The consumer sets busy then captures
pending with an exchange, so publication after that exchange remains pending for
a later batch. The shared ring lock serializes the visible ring accesses, while
count exchanges are separate operations.

The stop polling routine checks pending and busy only. It ignores staged and does
not acquire this ring lock. There can be queued-but-unpublished objects, or a
captured publication count not yet added to pending, while both polled fields are
zero. Thus submission exclusion is a specific missing requirement, not merely a
general concurrency caution. This does not prove a native shutdown race: an outer
caller may already enforce that exclusion, and its identity remains unresolved.

[Counter helpers](../../engine/loading_destruction.py) preserve the separate
staging, publication and batch-capture boundaries with int32 arithmetic. Tests
show the stop-poll blind spot, later publication surviving an earlier capture,
zero-count notification suppression and signed overflow. They model neither ring
growth nor resource destruction and must not be exposed as a native pause API.


## Ring growth, copy order and allocation boundary

The growth helper preserves the oldest `min(count, requested_capacity)` entries
for ordinary nonnegative ring geometry. It copies the suffix beginning at the read
index, then the wrapped prefix if needed. It resets both indices, replaces the
storage and records count and write index as the retained count. The write index
is not reduced modulo capacity at this point, even on a preserving shrink that
leaves the ring full. The destruction caller grows by 1024 rather than shrinking.

```text
retained = min(old_count, requested_capacity)
first = min(retained, old_capacity - old_read_index)
second = retained - first
copy(new_buffer, old_buffer + old_read_index, first)
if second > 0:
    copy(new_buffer + first, old_buffer, second)
# On the preserving replacement path:
read_index = 0
write_index = retained
count = retained
capacity = requested_capacity
```

Equal capacity with preserve enabled returns unchanged. Equal capacity with
preserve disabled clears indices/count without reallocating. A different capacity
with no retained data takes the clear/free then fresh-allocation path. Fresh
allocation checks for null and sets capacity zero on that branch. In contrast,
the nonempty preserving path passes its allocation result to the copy helper
without a visible null check. Whether the allocator throws, terminates or supplies
other guarantees remains unresolved.

This qualifies the insertion invariant: after an empty-ring allocation returns
null, the visible insertion check skips the object write, yet the staged count
increment still occurs. We have not observed this branch live and cannot claim a
recoverable out-of-memory contract. For nonempty preserving growth, treating null
as a no-op would also misrepresent the inspected control flow.

[The resize planner](../../engine/loading_destruction.py) implements valid bounded
ring copy geometry and metadata only. It neither allocates nor releases objects,
and explicitly excludes signed overflow and allocation-size overflow. Tests check
wrapped growth, oldest-entry retention on shrink, the full write index and equal-
capacity/nonpreserving branches. This permits future owned implementations to use
the known FIFO geometry while choosing and labeling their own allocation policy.


## Request processing follow-up

The loading-loop request phase now connects through a temporary processing
wrapper to resource publication and its surrounding callback passes. Queue
selection skips null entries; request kind/result/reprocess fields choose
processing or an alternate callback. Active request clearing precedes release
under the ring guard. See [animation resource research](research/animation.md)
under Loading-request cadence connected for pseudocode and unresolved contracts.
This is request-driven work, not a proved physics or animation frame boundary.


## Composed retirement-to-loading inspection probe

Run `python3 -m engine.examples.retirement_loading_probe` to inspect a synthetic
serial handoff from holder release through retirement consumption, loading
publication and batch consumption. This composes the local rules documented in
[holder retirement](ANIMATION_CONTEXT_RETIREMENT.md#deferred-holder-consumer-and-disposal-boundary)
with this document's staged/pending/busy counter rules. It does not run the game.

Every trace row includes retirement occupancy, loading occupancy, staged count,
a captured-but-not-yet-published count, pending, busy and remaining batch work.
The exact stop-poll predicate is shown separately from completion claims.
The ordinary example demonstrates three distinct states where the poll passes
although work remains: a queued retirement holder, a staged loading item, and a
captured publication count before its add to pending. After batch capture,
pending is zero but busy keeps the poll false. The probe records destructor/free
requests; it does not execute or claim successful disposal.

Calling `probe(reacquired_count=True)` supplies a second scenario: the holder's
count becomes nonzero before consumption. The retirement entry is consumed and
its queued bit cleared, but no loading item or destructor request follows. This
scenario change is authored input, not a recovered native acquisition API.

The operation schedule, one-object input and sufficient-capacity assumption are
explicit fixture choices. Callback mutation, exceptions, concurrent producers,
allocator failure and native shutdown exclusion remain outside the probe. An
empty final trace state is not evidence of a safe native plugin unload.

## Executable loading destruction insertion

`engine.loading_destruction_enqueue.enqueue_loading_destruction` now implements
producer `0x118d870..0x118d90f`. It holds loading-owner +0x1d8, attempts growth by
1024 when ring capacity is no greater than count, re-reads the resulting header,
and inserts only if space exists. The ring starts at owner +0x268. Its separate
staged uint32 at +0x28c increments unconditionally before unlock, including a
normal-return growth service that leaves the queue full. No payload-null gate is
present in this producer. Returned insertion/growth diagnostics are authored.

This is the mode-zero dispatcher called by the retirement consumer. Its staged
word is the same +0x28c captured by the consumer's outer handoff and transferred
to +0x288. The scope model's raw `worker.pending` input represents that staged
word; it must not be confused with the loading consumer's published pending count.
The existing signed counter helpers and this raw uint32 field model share the
same bits; interpretation at signed loop gates remains explicit.

The [producer comparison](../../native/snow_host/loading_destruction_enqueue_validation.json)
checks 48 original-instruction cases with supplied locks/growth, including empty,
full and available-space rings, replaced storage, staged wrap and null/non-null
payload tokens. Fields, slot writes and service order match the model. Three
public tests additionally compose it with the reconstructed resize implementation:
wrapped growth preserves pointer order, while empty allocation failure leaves
count zero but staged one. That test confirms the local counter mismatch; it does
not establish the game's actual allocator failure policy or recovery behavior.

The mode-zero payload path is therefore linked to concrete loading queue and
publication fields. Native resource ownership, the consumer's full failure path,
concurrent submission exclusion and shutdown still require separate proof.

## Executable destruction batch

[The batch model](../../engine/loading_destruction_batch.py) reconstructs
`0x1193b80..0x1193caf`. Owner pending +0x288 is exchanged to zero after busy
+0x290 is set. The captured uint32 is interpreted as signed for the loop gate.
Each iteration takes the ring lock +0x1d8, pops only if signed count +0x270 is
positive, then unlocks before allocation lookup, virtual destruction with flag
zero and allocator release. Metadata is captured before destruction. Allocation
services, storage retention and synchronization remain caller responsibilities.

The retained pointer is reset once per batch, not per iteration. Therefore:

- A wholly empty ring with positive captured budget makes no destruction calls.
- After a nonnull pop, an empty ring retains that pointer and repeats the
  lookup/destruction/free sequence for each remaining iteration.
- A subsequent null pop clears the retained pointer and suppresses subsequent
  destruction calls while the ring remains empty.
- Publication during destruction remains pending for the next batch; it does
  not extend this batch's captured budget.
- A captured count with the sign bit set is cleared without popping anything.

[Original-instruction comparison](../../native/snow_host/loading_destruction_batch_validation.json)
passes 144 cases with supplied lock, allocation and destruction services. It
checks service order and pending/busy/ring state with wrapped indices, null
slots, short queues and controlled publication during destruction. Synthetic
objects remain readable after the supplied free operation. This proves repeated
calls in the controlled shortage case, not an observed native double-free, a
reachable gameplay mismatch or a recovery policy. The model's ring geometry is
nonnegative and valid; native signed division at malformed indices is outside
its contract. Callback exceptions and concurrent teardown remain unqualified.
