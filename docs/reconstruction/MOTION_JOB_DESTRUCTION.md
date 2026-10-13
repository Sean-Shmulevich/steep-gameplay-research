# Motion job destruction and the outer lifetime requirement

The action-owner teardown invokes a range-job destructor on the same embedded
motion and pre-physics members identified in
[motion queue assignments](MOTION_QUEUE_ASSIGNMENTS.md). The local destructor
sequence is now decoded. It does not establish a safe native stop or drain API.

## Range storage cleanup precedes the base wait

The range destructor clears the remaining receiver count unconditionally. If the
array ownership flag is set, it passes a non-null storage pointer through an
allocator-related lookup and virtual release path, then clears storage and
capacity. It finally tail-calls the base job destructor.

```text
destroy_range_job(job):
    job.remaining = 0
    if job.owns_receiver_storage:
        if job.storage != null:
            release_through_allocator(job.storage)
        job.storage = null
        job.capacity = 0
    destroy_base_job(job)
```

The allocator helper internals are not decoded here. The established fact is the
release-call ordering and receiver argument, not complete allocation semantics.
Borrowed storage is not nulled or freed by this local branch, although the active
count is still cleared. This is destruction-time behavior, not the normal range
claim path and not permission to zero a live job's count.

## The base wait is conditional

The base destructor replaces the object's table, then checks a separate wait flag.
When set, it spins until the job state equals zero and outstanding dispatches are
not positive. Each iteration reads state, performs a locked stack operation, reads
the outstanding count, and pauses before retrying when either condition fails.
The two reads do not form an atomic snapshot.

```text
destroy_base_job(job):
    install_base_table(job)
    if job.wait_on_destroy:
        repeat:
            state_nonzero = (job.state != 0)
            locked_stack_operation()
            outstanding_positive = (job.outstanding_dispatches > 0)
            if not state_nonzero and not outstanding_positive:
                break
            processor_pause()
    clear_selected_callable_owners(job)
    destroy_dependency_storage(job)
    destroy_embedded_synchronization(job)
```

Cleanup helper names describe their local role and do not imply their complete
failure or platform semantics. The common base constructor initializes the wait
flag to zero together with its neighboring byte. Later flag writers remain open.
The wait tests outstanding dispatches rather than directly testing the separate
execution count. Normal accounting relates those counters, but that does not make
their storage interchangeable.

## Consequence for stepping and modding

The optional base wait occurs after the derived range storage cleanup. It cannot
by itself establish that in-flight receiver visitors were safe before that cleanup.
The action-owner destructor also destroys other members before these motion jobs.
Any enclosing stop, unregister or submission-exclusion contract must be found at
the caller or another lifecycle boundary.

This is not evidence of an original-game use-after-free. An outer invariant may
require jobs to be inactive before destruction. It is evidence against using this
destructor, its remaining-count clear or its optional spin loop as a stand-alone
pause/drain mechanism in a modding API.

The independent controller continues to require exclusive ownership and serialized
submission. Native release still requires proving new submissions are excluded,
claimed callbacks have returned and owners remain alive throughout observation.
No unsafe destructor behavior is copied into the independent runtime.

## Verification and next targets

The full range-destructor path was decoded across its chained exception-directory
segments, followed through its tail call to the base destructor. The owner member
receivers match construction and setup. The analyzed image SHA-256 is
`32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`.
No live game was used.

Next targets are writers of the wait-on-destroy flag and callers of action-owner
teardown. Neither this action owner nor these job destructors close the separate
[engine event-owner destruction gap](ENGINE_OWNER_DESTRUCTION.md).
