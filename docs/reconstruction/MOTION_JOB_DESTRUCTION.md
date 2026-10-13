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
flag to zero together with its neighboring byte. The ordinary submission writer is now joined below; other possible writers remain open.
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

## Submission writer and enclosing owner follow-up

A fresh aligned instruction scan located the ordinary submission routine's store
to the exact wait-flag field. It unconditionally sets the flag to one after its
state-dependent request/begin branch and before releasing the job lock. This is
the previously described usage flag in [rearm](SCHEDULER_REARM.md) and `usage` in
the independent mixed scheduler. Submitting an already scheduled job still sets
it, without taking the unscheduled request-increment branch.

```text
ordinary_submit(job):
    lock(job)
    if job.state == UNSCHEDULED:
        job.requested += 1
        if job.holds == 0:
            job.begin()
    job.wait_on_destroy = true
    result = (job.state == SCHEDULED)
    unlock(job)
    return result
```

This excerpt omits the submission routine's surrounding diagnostic and helper
calls; it expresses the local state/flag sequence only. Ordinary finalization in
the inspected path does not clear this flag. Dependency-triggered begin is a
separate entry and does not acquire the submission flag merely by running work.
Do not infer that every active downstream job has the flag set.

The bounded direct-call search also identifies an enclosing destructor that reads
an owned action-graph pointer, checks it for null, calls the graph teardown, then
releases its allocation through the allocator interface. The immediate pre-call
path contains allocator bookkeeping, not an established stop/drain operation.
This adds a containing-owner edge; it does not identify all virtual callers or
prove absence of an earlier outer barrier.

Two independent-model tests cover repeated submission without a second request,
flag retention after completion and dependency begin without direct submission.
They validate already implemented flag behavior, not actual destruction or native
thread safety. The next missing join is the enclosing owner's lifecycle caller
and its submission-exclusion contract. Other flag writers and aliases remain
outside the bounded scan.

## Containing-owner construction and deleting destructor

A further pass matches the containing owner's constructor and destructor by their
installed table. Construction allocates the action graph, calls its known graph
constructor when allocation succeeds, and stores the result in the same owned
member that teardown reads. The graph constructor is the one already joined to
the motion and pre-physics jobs. A null allocation follows a local null-result
path; no broader allocation failure/recovery contract is inferred.

The containing table's first entry resolves to a deleting-destructor wrapper:

```text
construct_containing_owner(owner):
    initialize_owner_base_and_members()
    graph = allocate_action_graph_storage()
    if graph != null:
        construct_action_graph(graph)
    owner.action_graph = graph
    initialize_remaining_members()

teardown_containing_owner(owner):
    install_containing_owner_table(owner)
    graph = owner.action_graph
    if graph != null:
        allocation_info = lookup_allocator_metadata(graph)
        destroy_action_graph(graph)
        release_graph_allocation(graph, allocation_info)
    destroy_other_owner_members()

deleting_destructor(owner, flags):
    teardown_containing_owner(owner)
    if flags & 1:
        release_owner_storage(owner)
    return owner
```

The returned pointer is the observed ABI result, not a usable object-lifetime
handle after release. The wrapper passes the owner allocation size to its release
helper. No separate stop operation appears in that wrapper before teardown.

This closes the storage identity chain from containing-owner construction through
action-graph construction to motion-job teardown and allocation release. It does
not name the containing owner from unsupported RTTI or prove its lifecycle caller.
The bounded aligned direct-call search found the deleting wrapper as a caller of
the owner teardown, but found no aligned direct call to its constructor within the
searched exception-directory ranges. Indirect factories, leaf functions lacking
those ranges and protected code remain possible. Neither negative search is an
exhaustive absence proof.

The next productive static target is the factory/registration route supplying this
owner and the virtual caller invoking its deleting destructor. Repeating searches
only for direct calls to the inner motion destructor will not answer submission
exclusion. Live owner/request identity and outer engine-event lifetime remain
separate unresolved requirements.
