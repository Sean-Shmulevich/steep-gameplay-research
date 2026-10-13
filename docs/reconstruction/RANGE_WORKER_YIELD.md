# Range worker yield signals and enqueue counters

A focused static join identifies the two shared values tested after each receiver
range. They are fields of the same global queue manager passed to ordinary enqueue.
This supersedes the deliberately unnamed values in the earlier
[batch-epoch audit](SCHEDULER_BATCH_EPOCH.md).

## Storage identity and writers

The ordinary begin path passes the global queue-manager object to enqueue. The
range worker reads two absolute fields that match that manager's enqueue-change
counter and front-insertion counter by base/member arithmetic.

Ordinary enqueue increments the change counter after insertion, state assignment,
aggregate-limit accounting and queue unlock. The front-insertion branch also
atomically increments a separate counter after its first-slot write, before the
common state/limit/unlock/change-counter path. The follow-up below joins constructor zeroing and flagged queue removal to that
counter. Its queue-membership interpretation requires valid membership and stable
flags; it is not a count of all executing jobs.

## Exact yield rule

After successfully claiming its first range, the worker captures the queue-change
counter before calling its optional context-entry function and receiver visitor.
After the visitor returns, it checks:

```text
captured_change = queue_manager.change_counter
enter_optional_context()
repeat:
    visit_current_claimed_range()
    if queue_manager.change_counter != captured_change:
        break
    if job.early_exit_enabled and queue_manager.front_counter != 0:
        break
    if not claim_next_range():
        break
leave_optional_context()
```

The captured value is retained across subsequent claims in this worker invocation.
The change comparison is equality on the stored 32-bit value. The front-counter
check is nonzero, not signed-positive. It applies only when the job flag is set.
The constructor initializes that job flag false; later flag setters remain open.

A counter change does not cancel the current claimed receiver range. The check
occurs after its visitor returns and before another claim. Work can remain queued
for another dispatch after this worker returns. Other workers may meanwhile have
claimed or completed other ranges.

## Interpretation and limitations

These observations support a queue-change yield mechanism: newly enqueued work
can cause the current range worker to stop taking further ranges. They do not
establish a frame boundary, input generation, fixed timeslice, priority fairness
or a pause request. Counter wrap can hide changes if an entire 32-bit cycle occurs
between observations; no unbounded generation guarantee follows.

`engine.queue_producers.range_should_yield` implements the exact local predicate
with explicit uint32 change values, a Boolean job flag and signed-int32 front
counter. Its tests include disabled gating, nonzero negative values and wraparound
inequality. The helper does not synthesize native counter updates or terminate
callbacks. The mixed-scheduler integration below now supplies the reconstructed counter lifecycle.

The instruction check joined the range worker, ordinary begin and all chained
segments of enqueue in image SHA-256
`32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`.
No game execution or live counter observation was performed.

## Counter removal and initialization follow-up

The queue-manager constructor zeroes the change, aggregate-limit and front counters.
A removal routine uses the same category/lowest-required-bit routing as enqueue,
locks the selected queue, searches for the job pointer and invokes the array erase
helper on a match. It then decrements the front counter if the job's front flag is
set, writes DONE to the job and unlocks the queue.

```text
remove_queued_job(manager, job):
    queue = resolve_same_destination_as_enqueue(manager, job)
    lock(queue)
    removed = find_and_erase_job_pointer(queue, job)
    if job.front_flag:
        atomic_decrement(manager.front_counter)
    job.state = DONE
    unlock(queue)
```

The caller ignores the search helper's Boolean result. Therefore decrement is
conditional on the flag, not on a proved successful removal. Balanced membership
and unchanged routing/front flags are input invariants, not checks supplied here.
Under those invariants, zero initialization plus enqueue increment and removal
decrement support counting flagged queued jobs. Changing flags while queued could
invalidate that interpretation; no such runtime behavior is asserted.

The removal routine does not increment the enqueue-change counter. A range worker
may observe a nonzero front counter even when no enqueue occurred since its own
captured change value. Conversely, removing a flagged callback from the queue can
reduce this counter before the callback body returns. It must not be used as a
running-callback count or universal idle predicate.

Three aligned direct callsites enter removal when a job state is SCHEDULED;
other branches set DONE without queue removal. These are bounded callsite findings,
not an exhaustive writer inventory or proof of every runtime state transition.

## Array shift arguments

The pointer search examines entries in increasing array order and invokes erase
at the first matching index. Erase passes the following byte-copy arguments before
decrementing logical count:

```text
destination = storage + index * 8
source = storage + (index + 1) * 8
bytes = (old_count - index - 1) * 8
```

Insertion at index zero updates count to old-count plus one, then passes source
storage, destination storage plus eight and old-count times eight bytes to the
same overlap-copy target. The caller then stores the new pointer in the first slot.
These arguments support ordered shifts rather than swap-with-last removal. This
pass does not independently reconstruct the runtime copy helper's implementation
or allocator failure semantics. It closes the array-helper index/length arithmetic
that the earlier enqueue note left open.

## Executable queue-change yielding

The mixed scheduler now maintains `queue_change` and `front_count` in snapshots.
Executable job definitions accept Boolean `front_insert` and `early_exit_enabled`,
both false by default. Front insertion uses an ordered prepend in the independent
Python queue; the inspected copy arguments support that ordering, while native
copy/allocator internals remain outside the reconstruction.

Enqueue increments the 32-bit change counter. Flagged insertion increments front
count; queue removal decrements it without changing enqueue generation. Flags and
routing are immutable within this adapter, and duplicate queue entries are not
permitted, preserving the accounting invariants described above.

A dispatch captures queue generation at its first successful claim. After each
claimed range's visitor returns, it applies `range_should_yield`. A true result
sets `yield_requested`, emits the observed counter values and prevents further
claims by that dispatch. `finish_dispatch` then permits the unclaimed remainder
to stay scheduled. A new dispatch captures a new generation and can resume it.
Helper dispatches use the same range execution rule. No current receiver callback
is cancelled or rolled back by yielding.

Four integration cases cover enqueue during a multi-receiver claim, later resume
without early successor release, the optional front gate, removal before callback
execution, and counter wrap. The symbolic explorer treats a yielded dispatch's
next action as finish rather than an endless attempt to claim again. Job-specific
native flag setters and platform concurrency remain unverified.
