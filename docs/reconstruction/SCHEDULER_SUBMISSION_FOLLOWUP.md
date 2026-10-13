# Scheduler teardown and submission-exclusion follow-up

The scheduler's concrete teardown chain is now connected to its owning objects. This pass did not identify a complete submission-exclusion gate. The newly established ordering tells us exactly where that gate must already have taken effect; it does not establish an original-engine race or make the destructor safe to invoke from an injected thread.

## Owner chain and destruction order

Construction links an enclosing object to a separately allocated manager, the manager to a separately allocated world scheduler, and the scheduler back to the manager as its owner. The corresponding cleanup chain follows those same fields:

```text
enclosing_object
    -> manager
        -> world_scheduler
            -> timing history and embedded jobs
```

The enclosing object's destructor first destroys and frees two other owned objects through their respective virtual entry points, clearing their slots. It then destroys and frees the manager. The two earlier virtual destructors have not been resolved in this pass: they could contain relevant synchronization. Their presence prevents interpreting the subsequently observed cleanup order as proof of missing upstream synchronization.

The manager destructor does the following in this order:

```text
destroy_manager(manager):
    if manager.scheduler != null:
        allocator_metadata = lookup_allocation(manager.scheduler)
        destroy_world_scheduler(manager.scheduler)
        free_allocation(manager.scheduler, allocator_metadata)

    lock(global_backend_guard)
    if manager.backend_object != null:
        allocator_metadata = lookup_allocation(manager.backend_object)
        destroy_backend_object(manager.backend_object)
        free_allocation(manager.backend_object, allocator_metadata)
    unlock(global_backend_guard)

    release_remaining_manager_owned_handles_and_arrays()
    destroy_manager_collection_locks()
```

The global backend guard is acquired **after the scheduler has been destroyed and freed**. This local acquisition cannot be cited as the lock that excluded submissions during the preceding scheduler destruction. A separately held outer lock or the earlier virtual cleanup calls remain possible, unproven sources of exclusion.

## Actual scheduler cleanup sequence

The scheduler cleanup clears its stored root-job pointer, releases the timing-history array, then destroys its embedded jobs. The job sequence follows descending storage placement for seven variable-work jobs, followed by three callback jobs and the remaining base job wrapper.

```text
destroy_world_scheduler(scheduler):
    scheduler.root_job_pointer = null
    release_history_array(scheduler.timing.history)

    for job in scheduler.variable_work_jobs_in_reverse_storage_order:
        destroy_variable_work_job(job)

    for job in scheduler.three_callback_jobs_in_reverse_storage_order:
        job.callback_dispatch_pointer = null
        destroy_base_job(job)

    destroy_remaining_base_job_wrapper(scheduler)

release_history_array(history):
    saved_pointer = history.pointer
    history.next_write = 0
    history.oldest = 0
    history.count = 0
    if saved_pointer != null:
        release_allocation(saved_pointer)
    history.pointer = null
    history.capacity = 0
```

Clearing the root pointer is an observed write, not yet a submission gate. No proof establishes that every submitting thread reads that pointer, that it observes the write atomically with lifetime changes, or that workers holding an already fetched pointer are excluded.

The history is released before the per-job cleanup calls. Likewise, the variable-work job cleanup zeroes its logical work count and, when its owned-storage flag is set, releases its work-array allocation before calling the base-job cleanup. That ordering is consistent with an upstream lifecycle precondition that submissions and relevant users are already excluded. Establishing that precondition remains the required next step.

## Conditional drain inside base-job destruction

The base-job cleanup checks its previously documented start/usage flag. When set, it busy-waits until lifecycle state is zero and signed outstanding execution/completion accounting is nonpositive. Its loop includes a memory barrier and processor pause instruction. It does not acquire a demonstrated global submission gate.

```text
destroy_base_job(job):
    install_base_job_vtable(job)
    if job.start_or_usage_flag:
        repeat:
            state = load(job.lifecycle_state)
            memory_barrier()
            outstanding = signed_load(job.outstanding)
            if state == 0 and outstanding <= 0:
                break
            processor_pause()
    clear_selected_callback_and_queue_links(job)
    destroy_dependency_list(job)
    destroy_job_lock(job)
```

This is a destruction-time conditional drain. It is not a pause API. It also cannot retroactively protect work buffers already released by derived cleanup. The validity of that sequence depends on the caller's lifecycle guarantees, which this pass has narrowed but not yet proved.

The existing [scheduler research](research/scheduler.md) distinguishes generation-sensitive completion, callback caching and publication. Those constraints remain in force. A zero state/counter observation cannot pin the manager, the scheduler or a callback fetched earlier by another worker.

## Precise next evidence needed

The next static investigation should resolve the two virtual objects destroyed before the manager, using their constructors and installed virtual tables. Determine whether either cancels/unregisters the scheduler, waits for an enclosing generation or owns a submission lock. Separately trace callers that submit the scheduler's root job and compare their synchronization object with that earlier teardown path. Only a common exclusion relationship can support a safe original-engine step boundary.

Do not start by calling this destructor or base drain from an arbitrary thread. The already recovered sequence includes allocation release, callback invalidation and lock destruction. A live test should initially observe the natural teardown/submission events after their concrete owner identities are established.

## Evidence and limits

This pass used only the studied local image and existing static exports. The world-scheduler cleanup's 36 exported instructions were independently matched against the image. Owner cleanup, enclosing cleanup and helper bodies were inspected within their exception-table function/chained-fragment bounds. No game, debugger or process-memory operation was used. Function hashes below identify checked code without publishing executable payloads or making addresses part of the engine API.

| Checked function role | Bounded bytes | SHA-256 |
| --- | ---: | --- |
| Enclosing owner cleanup | 675 | `93dbf52dd3118b3e8300ff37176b080fe2e471fabc18bd12cd5b58440bf0235d` |
| Manager cleanup | 466 | `62c26171b20bddfea5e254582bbb7998bfaa701fd4ca43d3e61fb569791e4b07` |
| World-scheduler cleanup | 191 | `03b78d836673a89b813ddf4526178abcf475d1b445c5d1526fa805a94abc4d31` |
| History-array release | 117 | `c6e231a9315fb42ae586ebc87436da4d5d02bd09586c5b8c2ab5be9023d6cc61` |
| Variable-work job cleanup | 122 | `ce7319e63d0c9cad05396c0ac4605bb360f6bc74be881e622b2154a19703a095` |
| Base-job cleanup | 111 | `62d27b0041cb961cd106dfc43888c1aeb25e5fed72dd488d952de4f73990be99` |

Image SHA-256 remains `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. Construction and timing details are in the [lifetime audit](SCHEDULER_LIFETIME_AUDIT.md). No claim of exhaustive submission coverage or resolved exclusion follows from this bounded teardown trace.
