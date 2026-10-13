# Ordinary queue eligibility and selection

The ordinary selector does more than enforce a concurrency limit. It scans three ordered categories, prefers the current worker's local queue within each category, applies job-specific eligibility methods, and selects the smallest integer occupancy score. The receiver range job uses its limit as an execution cap. The callback job's eligibility method always returns true, so applying the same cap to every reconstructed job would change the inspected behavior.

This follows [scheduler dispatch and rearm](SCHEDULER_REARM.md). The routine and field names below are explanatory aliases. No game execution or emulation was used.

## Category and queue order

The category selector loops over indices zero, one and two. For each index it first asks the worker-local queue, then the corresponding shared scheduler queue. It returns as soon as either yields a job. Therefore a shared candidate in category zero precedes a worker-local candidate in category one.

```text
select_for_worker(scheduler, worker):
    rejected_by_affinity = false
    for category in [0, 1, 2]:
        observed_change = scheduler.change_counter
        job = select_queue(worker.local[category], worker,
                           skip_affinity=true, rejected_by_affinity)
        if job is null:
            job = select_queue(scheduler.shared[category], worker,
                               skip_affinity=false, rejected_by_affinity)
        if job is not null:
            if scheduler.change_counter != observed_change:
                notify_worker_candidates(scheduler)
            return job
    return null
```

The categories' external names or priorities are not assigned here. This establishes traversal order, not fairness or starvation guarantees. The local and shared containers are distinct caller-supplied queue addresses; the flag suppresses only the explicit affinity tests described below.

## Eligibility gates

The queue helper first checks its count outside the queue lock. A zero count returns no job. Otherwise it takes the lock, rechecks the count, and walks the stored job pointers in array order.

For each job it conditionally invokes an eligibility callable if that callable's storage is present. A false result rejects the job. It then invokes the job's virtual eligibility method; false also rejects it.

For shared queues only, the job's required-mask and excluded-mask fields are compared with the worker's mask:

```text
affinity_ok(job, worker):
    if job.required_mask != 0:
        if (worker.mask & job.required_mask) == 0:
            return false
    if (worker.mask & job.excluded_mask) != 0:
        return false
    return true
```

A required mask means any overlapping bit, not all required bits. An excluded overlap rejects even when the required-mask test succeeds. An affinity rejection sets a caller-provided byte flag. The inspected category caller initializes and passes that flag but does not use it to change the category order.

These operations run under the queue lock. That fact does not specify the optional callable's application meaning or prove an independently sampled job is eligible.

## Selection score and tie rules

After eligibility and affinity pass, an `INT_MAX` job limit is replaced in the job itself by a shared default integer. The selector computes:

```text
if job.limit > 0:
    score = trunc_toward_zero(int32(job.executions * shared_default)
                             / job.limit)
else:
    score = shared_default
```

The multiplication is a 32-bit signed operation and division is signed. Ordinary nonnegative, nonoverflowing values behave as an occupancy ratio scaled by the shared default. The machine arithmetic should not be silently replaced by unlimited-precision rational comparison for arbitrary inputs. Exceptional signed-division inputs are outside the ordinary examples here.

The current best score starts at `INT_MAX`. A candidate replaces the best only if its score is strictly smaller. Equal scores retain the earlier candidate. After selecting a score of zero, the loop exits immediately.

```text
best_job = null
best_score = INT_MAX
for job in queue.array_order:
    if not eligibility_and_affinity_pass(job):
        continue
    resolve_default_limit_if_needed(job)
    score = occupancy_score(job)
    if score < best_score:
        best_job = job
        best_score = score
        if score == 0:
            break
```

For a shared default of eight, eligible jobs with execution/limit pairs `1/4` and `1/2` score two and four. The first has preference even if it occurs later in the array. Two idle eligible jobs score zero; the first wins without evaluating the second. The shared default's producer and supported range remain separate evidence questions.

## Why max concurrency is job-specific

The receiver range job's virtual eligibility method resolves the same `INT_MAX` sentinel in place and returns the signed comparison:

```text
receiver_job_eligible(job):
    if job.limit == INT_MAX:
        job.limit = shared_default
    return job.executions < job.limit
```

In contrast, the reviewed ordinary callback-job table binds this virtual method to a constant true result. Its reservation callback removes the job from the queue and marks it done before its callable runs, as documented in [the engine-loop handshake](ENGINE_LOOP_HANDSHAKE.md). For this type, the limit still affects selection score; the inspected eligibility method does not implement a generic execution-count cap.

A reconstruction should therefore separate a job-kind eligibility rule from its score denominator. A single unconditional `executions < max_concurrency` adapter would conflate those two mechanisms. Other job tables may supply further eligibility implementations and must be mapped individually.

## Reservation and change notifications

Once a best job is found, the queue helper increments its outstanding-dispatch count and execution count, invokes its reservation method, then releases the queue lock and returns the pointer. The selected job is already accounted for before the worker enters its body.

After selection, if the scheduler comparison counter changed, the category caller traverses its worker list. For each worker it atomically changes a signed notification counter to `min(previous + 1, 1)` through a compare/exchange retry loop. If the successfully replaced value was negative, it invokes the worker's event operation. The meanings of the comparison counter's writers and the protected event operation are not assigned by this pass.

This notification traversal occurs after a successful selection. It is not a second pass that chooses a different job or overrides the category/score result.

## Verification and remaining scope

The three-category caller, queue helper and receiver eligibility method were freshly decoded from the image with SHA-256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. The callback eligibility binding was checked against the previously decoded concrete job table.

Unresolved inputs include category assignment producers, worker-mask meanings, optional eligibility callable bindings, the shared default's configuration, and alternate job types. The explicit helper dispatcher is a different entry path; this document does not impose ordinary queue selection rules on it. No whole-scheduler fairness, deterministic order across workers or live selection trace is claimed.
