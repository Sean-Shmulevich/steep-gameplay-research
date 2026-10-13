# Explicit wait-helper execution accounting

The [rearm audit](SCHEDULER_REARM.md) previously left reservation accounting for the explicit wait/helper dispatcher open. A complete fresh decode of that helper closes its local accounting sequence: it increments both outstanding-dispatch and execution counts before calling the same execution wrapper used by ordinary workers.

## Local sequence

The helper first calls the selected job's empty predicate. While that predicate is false, it obtains the current thread's scheduler context from thread-local storage, increments the two counts, invokes the execution wrapper, and tests the predicate again. The wrapper calls the concrete worker and then the previously inspected completion routine.

```text
help_and_wait(job):
    if not job.is_empty():
        context_slot = current_thread_scheduler_context_slot()
        while true:
            atomic_increment(job.outstanding_dispatches)
            atomic_increment(job.executions)
            execute_with_context(context_slot.value, job)
            if job.is_empty():
                break

    while true:
        state_is_nonzero = job.lifecycle_state != 0
        memory_barrier()
        outstanding_is_positive = signed(job.outstanding_dispatches) > 0
        if not state_is_nonzero and not outstanding_is_positive:
            return
        processor_pause()
```

The two final loads are separate, with a locked instruction between them. They are not an atomic snapshot. The final loop does not directly read the execution count; normal completion already updates that count and decrements outstanding accounting last. Signed-positive outstanding testing must not be replaced by an unqualified nonzero comparison when describing the instructions. Valid nonnegative accounting remains a caller/lifecycle assumption.

Unlike ordinary queue selection, this helper does not invoke the reservation callback or check the queue's concurrency limit before executing the worker. It also does not obtain a new arbitrary job from a queue. It helps the specific receiver passed by its caller. Correct use therefore requires a compatible job type, active request and thread context. It is not a generic substitute for queue dispatch.

In particular, the new engine-loop audit identifies a callback-job type whose empty predicate is always false and which changes lifecycle at queue reservation. Applying this helper to that type without an additional proven protocol would erase those distinctions. The local helper arithmetic alone does not authorize doing so.

## What this closes

Both inspected direct callers of the execution wrapper now establish execution accounting before entering the concrete worker:

- The ordinary queue path reserves a selected job, increments counts and calls its reservation method.
- The explicit helper increments counts itself for each attempted worker invocation, then waits on lifecycle and outstanding accounting.

This strengthens the worker-return-before-finalization argument for these two paths. It does not prove that every possible native worker invocation uses the wrapper, exclude new submissions, retain a destroyed owner or establish a safe pause point. A caller must still protect the job and its receiver storage throughout helping and waiting.

The predicate ending the helping loop is also not the entire drain condition. Empty claim storage can coexist with callbacks still running on other threads; the subsequent state/outstanding loop covers a different condition.

## Verification

The full contiguous helper spans 151 bytes and decodes to 43 instructions. Its SHA-256 is `fcd5212a30dfba2e742bac859d03df18d48c67c10e15e86274664ee1a733cc3f`. The analyzed image SHA-256 is `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`.

A bounded scan found and instruction-validated two direct wrapper callsites: this helper and the ordinary worker loop. That scan is not an exhaustive inventory of indirect calls or worker entry paths. Earlier retained findings already described the helper's increments; this pass reconciles that evidence with the current rearm guide and verifies the complete helper against the image. No live game execution occurred.
