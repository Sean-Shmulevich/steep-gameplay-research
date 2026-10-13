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
population staying consistent. We have not traced their producers and do not
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

Next evidence should join the pending-count and ring writers, then identify the
outer shutdown caller. That is more useful than treating these two zero fields as
an engine-wide pause signal.
