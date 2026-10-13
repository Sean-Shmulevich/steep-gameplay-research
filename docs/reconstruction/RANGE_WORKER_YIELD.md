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
common state/limit/unlock/change-counter path. The front counter's decrement and
reset paths have not yet been decoded in this pass. It must not be assumed to be
an exact live priority-job count until those paths are joined.

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
callbacks. Connecting counter lifecycle into the runtime remains separate work.

The instruction check joined the range worker, ordinary begin and all chained
segments of enqueue in image SHA-256
`32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`.
No game execution or live counter observation was performed.
