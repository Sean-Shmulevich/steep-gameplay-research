# Motion-batch dispatch, completion and rearm

The [batch-epoch audit](SCHEDULER_BATCH_EPOCH.md) established that the receiver count reaches zero when ranges are claimed, before their callbacks finish. This follow-up identifies the ordinary worker-thread caller and the separate execution accounting that covers those callbacks. It also identifies the action graph's conditional entry and terminal nodes. The link from one completed graph request to the next gather remains unresolved.

This is static evidence. No game was launched or attached to, and no original code payload is included here. Names below describe field roles established by the inspected operations; they are not recovered source declarations.

## The concrete dispatch path

A scheduler worker thread selects a job through a two-category selection helper. The selected category's queue routine checks eligibility, including the concrete job's concurrent-execution limit. While holding the category container lock, it increments both the job's outstanding-dispatch count and its execution count. It then invokes the job's reservation callback and returns the selected job to the thread.

The thread invokes the execution wrapper. That wrapper calls the job's concrete range worker, then the completion routine. Thus the execution count already includes the interval between queue selection and entry into the range worker. Counting only callbacks currently inside the visitor would miss that interval.

```text
select_job(category):
    lock(category)
    job = find_eligible_job(category)
    if job exists:
        atomic_increment(job.outstanding_dispatches)
        atomic_increment(job.executions)
        job.reservation_callback()
    unlock(category)
    return job

worker_thread_iteration():
    job = select_from_scheduler_categories()
    if job exists:
        install_execution_context(job)
        job.run_range_worker()
        restore_execution_context()
        finish_dispatch(job)
```

This summarizes one concrete ordinary dispatch path. It does not assert that every invocation of the worker must pass through that selector. An explicit wait/helper path also calls the execution wrapper and requires its own reservation accounting audit before extending the claim to all dispatchers.

## Completion separates empty work from finished callbacks

The completion routine first decrements `executions`. A scheduled job whose local empty predicate succeeds can move to the done state. For this receiver job, the predicate tests the remaining claim count, not the number of active callbacks.

Finalization requires the done state and `executions == 0`, checked again under the job lock. Finalization releases active outgoing dependencies and returns the lifecycle state to unscheduled. The completion routine decrements `outstanding_dispatches` last.

```text
finish_dispatch(job):
    atomic_decrement(job.executions)

    if job.state == SCHEDULED and job.is_empty():
        lock(job)
        if job.state == SCHEDULED and job.is_empty():
            mark_done_and_remove_from_scheduler(job)
        unlock(job)

    if job.state == DONE:
        lock(job)
        if job.state == DONE and job.executions == 0:
            job.finalize()
        unlock(job)

    atomic_decrement(job.outstanding_dispatches)

ordinary_finalize(job):
    lock(job)
    if job.outgoing_dependencies.active:
        release_dependencies(job.outgoing_dependencies)
    job.state = UNSCHEDULED
    finish_scheduler_bookkeeping_if_registered(job)
    unlock(job)
```

The enum names are explanatory labels for the observed states. Nested locking and helper details are abbreviated; this is behavioral pseudocode rather than a replacement lock implementation.

On this ordinary path, successors are released after the dispatched worker bodies have returned. They can be released before the predecessor's remaining bookkeeping and final outstanding-count decrement finish. Consequently `outstanding_dispatches == 0`, `executions == 0`, and an empty receiver count are different observations.

This closes a local lifetime distinction: the scheduler does not use receiver-count zero alone as the ordinary finalization test. It does **not** yet prove that the next gather is a successor of a suitable completion barrier.

## Request counts and dependency holds

The ordinary submit routine locks the job. If its state is unscheduled, it increments a requested count and invokes the begin method when no dependency holds remain. It also sets a usage flag. Submitting in a different lifecycle state does not take that same request-increment branch.

Ordinary begin snapshots `requested` into `started`, activates outgoing dependencies, and either queues nonempty work or completes an empty job through its finalizer. The begin method itself is not a universal wait for outstanding dispatches; its caller and lifecycle gates matter.

Activating an inactive outgoing dependency list increments each successor's hold count. A transition from zero holds to one also increments that successor's requested count. Activation then propagates through the successors' activation methods. Repeated activation of an already active list is gated.

Normal release marks the list inactive and decrements the successors' holds. On the last hold, the successor is locked. A mismatch between its started and requested counts makes it eligible for begin, subject to the separately inspected credit/defer gate.

```text
release_one_dependency(successor):
    previous_holds = atomic_fetch_add(successor.holds, -1)
    if previous_holds != 1:
        return
    lock(successor)
    if successor.started != successor.requested:
        if successor.credit_gate and successor.credits <= 0:
            successor.deferred = true
        else:
            consume_credit_if_required(successor)
            successor.begin()
    unlock(successor)
```

These counts distinguish requested work from started work under dependency holds. Their operations do not establish that either count is a global frame identifier. They also do not clear the receiver array.

## The action graph has a concrete conditional entry and terminal node

Graph construction creates a wrapper containing a separately allocated conditional job and an inline terminal job. Setup assigns the labels `UpdateActionWorldIsPausedBranch` and `UpdateActionEndNode` to these jobs. The conditional job holds two dependency lists; its constructor puts the inline terminal job in the secondary list.

Setup binds the branch callable to the graph's world receiver. Its inspected predicate is a signed world-field comparison against zero, returning true when the field is nonpositive. The label suggests its purpose, but this pass does not assign that field units or a complete pause-state interpretation.

The branch activation method pre-holds both dependency lists. Its begin method evaluates the callable, normally releases the selected list and routes the alternate list through a different dependency-release method. That alternate method calls a successor virtual method when the last hold is removed. Its full recursive effect is outside this audit, so it must not be silently equated with ordinary execution or ordinary completion.

```text
conditional_begin(branch):
    lock(branch)
    result = branch.world_predicate()
    if result:
        release_alternate_route(branch.secondary)
        release_dependencies(branch.primary)
    else:
        release_alternate_route(branch.primary)
        release_dependencies(branch.secondary)
    unlock(branch)
```

The primary route reaches the action gather through the graph's established predecessor chain. The terminal node receives several action-graph endings, including the physics end and animation end. Its begin method snapshots its request count, activates and releases its outgoing dependencies, and returns to the unscheduled state without a range-worker body.

The conditional begin differs from ordinary queued begin. Applying the ordinary begin's state/count pseudocode to every job table would erase this distinction. Likewise, the terminal node is a dependency-graph node, not evidence that all engine work everywhere has finished.

## The exact remaining join

The unclosed edge is the caller that activates or submits this particular conditional wrapper for request `n + 1`, together with the gate that prevents it from reaching gather while receiver ranges from request `n` remain active.

The inspected construction and setup establish the wrapper, its world callable, its primary gather route and its terminal node. They do not yet identify the runtime caller's dynamic receiver or demonstrate that the caller waits for this terminal node before rearming the wrapper. Direct references found during the bounded review chiefly identify setup and destruction; generic, indexed or aliased access remains possible. This is a search limit, not proof that no such caller exists.

The closure now has a precise condition to prove:

```text
all_prior_dispatches_using_receiver_storage_have_returned
    -> current_action_request_terminal_or_equivalent_barrier
    -> permission_to_rearm_the_same_action_graph
    -> next_gather_can_replace_receiver_storage
```

A nonempty gather may replace or reallocate storage. An empty gather preserves its header. Neither operation itself supplies the missing exclusion. Early worker exit with positive remaining count also still needs the outer request policy: finish the old request, explicitly reset it, or otherwise prevent its remaining receivers from crossing into a new request.

For an independent reconstruction, a caller-enforced request barrier or immutable per-request receiver arrays is a reasonable explicit policy. The original graph's equivalent policy is not claimed recovered here.

## Evidence and verification scope

The reviewed material includes the ordinary worker-thread loop, its two-category selector, the queue reservation sequence, the execution wrapper, completion/finalization methods, ordinary submission and dependency methods, and the action graph's wrapper constructor and setup. Concrete virtual-table bindings connect the receiver job to its range worker and empty predicate, and connect the branch and terminal jobs to their distinct begin methods.

The analyzed image SHA-256 is `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. The [batch-epoch audit](SCHEDULER_BATCH_EPOCH.md) records the separately verified range-worker hash. This pass establishes static caller and field relationships; it does not provide a live request trace, an exhaustive dispatcher inventory, or a universal storage-lifetime proof.
