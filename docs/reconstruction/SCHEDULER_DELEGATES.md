# Scheduler delegate dispatch contracts

The constructor-bound graphics delegate and a branch-job delegate share an
invocation adapter. Their enclosing dispatch contracts must remain distinct.

## Common invocation adapter

RVA `0x8ab390` receives function storage in RCX and receiver in RDX. It moves the
receiver to RCX and tail-jumps through the first qword of function storage.
The [invoker check](../../native/snow_host/graphics_delegate_invoker_validation.json)
verifies exact forwarding and preservation of the caller's return address.
It does not strip tags or determine a callback's return type.

The graphics binding is documented under
[graphics delegate invocation](ANIMATION_CONTEXT_RETIREMENT.md#graphics-delegate-invocation-adapter).
Its owner-relative delegate is not interchangeable with the existing probe's
image-backed virtual slot. Native installation remains unimplemented here.

## Branch dispatcher

Dispatcher RVA `0x11d14c0` has the following locally inspected behavior:

```text
branch_dispatch(job):
    lock(job + 8)
    receiver = job.delegate.context_word & ~3
    result = job.delegate.invoker(&job.delegate.function_storage, receiver)
    if low_byte(result) != 0:
        helper_A(job + 0x1b8)
        helper_B(job + 0x70)
    else:
        helper_A(job + 0x70)
        helper_B(job + 0x1b8)
    unlock(job + 8)
```

The delegate begins at job +0x198; context is +0x1a8 and invoker +0x1b0.
The two list services are `0x11d29e0` and `0x11e7ba0`, respectively. Their
semantics are deliberately not inferred from this caller alone. The dispatcher
appears as a stored function pointer at image RVA `0x28f53d0`; that reference
alone does not identify every receiver or establish the graphics-job route.

A [16-case connected instruction check](../../native/snow_host/branch_delegate_validation.json)
executes both this dispatcher and the common invoker. It tests all four context
tag combinations and predicate results 0, 1, 255 and 256. The last case follows
the false branch because only AL is tested. The check verifies decoded receiver,
lock/predicate/list-service/unlock order and the two selected list addresses.
The predicate, lock and list services are intercepted. Callbacks return normally;
no exception cleanup or concurrency guarantee is established.

## Remaining graphics binding gap

This branch dispatcher supplies concrete evidence of upstream tag stripping for
one scheduler job type. It cannot close the graphics route by analogy: it consumes
a predicate return byte, while the inspected graphics binding alone establishes
no such predicate contract. To install a graphics-phase observer, first identify
the concrete job table and its dispatch slot, follow that body into the delegate,
and qualify owner lifetime and slot ownership. Keep an observation wrapper's
calling convention tied to that confirmed route.


## Concrete graphics dispatcher now identified

The [live binding capture](../../native/snow_host/graphics_job_live_binding.json)
qualifies the graphics job at engine owner +0x218. Three startup samples agree:
table RVA `0x1e89618`, slot +0x40 target `0x65b1e0`, main delegate callback
`0x656c20`, invoker `0x8ab390`, and masked context equal to the engine owner.
Selector +0x5a was zero in those samples. This closes the concrete-table and
upstream-decoding gaps above for this observed binding. It does not sample the
callback's execution or establish selector stability across frame gates.

```text
graphics_job_dispatch(job):
    if (job.before.context & ~3) != 0 or job.before.function != null:
        job.before.invoker(&job.before.function, job.before.context & ~3)
    job.main.invoker(&job.main.function, job.main.context & ~3)
    if (job.after.context & ~3) != 0 or job.after.function != null:
        tail_call job.after.invoker(&job.after.function, job.after.context & ~3)
```

The before, main and after delegates begin at job +0xf0, +0x198 and +0x110.
Each record is 32 bytes. The main call is unconditional; its return is not used
for branch selection. Optional eligibility checks function/context, not whether
the invoker field is nonzero. A tag-only context with null function is skipped.
Do not assume a context-only record is safe with every invoker implementation.

A [32-case connected instruction check](../../native/snow_host/graphics_dispatch_validation.json)
executes this concrete dispatcher and the common invoker. It varies all context
tags, optional callback presence and callback return bytes. It verifies exact
before/main/after ordering, decoded receivers and normal return stack balance.
Synthetic callbacks supply no evidence about native mutation or exception safety.

The before/after records are candidates for bounded phase observation. No native
installation was attempted. An installer must preserve existing callbacks,
qualify the full descriptor and owner, prevent concurrent inconsistent updates,
and account for callers that already loaded an invoker. Image-vtable swapping
rules do not automatically establish those owner-relative delegate guarantees.
The read-only session stopped cleanly with saves/settings restored and original
DLL verified. No private heap addresses are included in the public receipt.

## Job teardown contract

Static inspection connects the live graphics table's deleting destructor at RVA
`0x652c70` to base teardown `0x11cb650`. The relevant normal path is:

```text
graphics_job_destroy(job, flags):
    job.main.invoker = null
    job.table = base_job_table
    if job.byte_194 != 0:
        repeat:
            state = read_u32(job + 0x54)
            stack_locked_or_zero()  // ordering instruction, not the job lock
            count = read_i32(job + 0x50)
            if state == 0 and count <= 0: break
            processor_pause()
    job.completion.invoker = null  // +0x168
    job.after.invoker = null       // +0x128
    job.before.invoker = null      // +0x108
    teardown_list(job + 0x70)
    destroy_lock(job + 8)
    if flags & 1: free_storage(job, 0x1b8)
    return job
```

The base constructor at RVA `0x11c8c40` initializes +0x50/+0x54 to zero
and the word at +0x194 to zero. It also clears the function, context and invoker
fields of the before/after/completion delegates. It does not initialize every
byte of those 32-byte records. This is a constructor default, not an observation
of the live job's current wait policy. Subsequent writers remain to be qualified.

The [36-case instruction check](../../native/snow_host/graphics_teardown_validation.json)
executes both destructors with synthetic job storage. It varies the wait flag,
state 0/1/2, count 0/1/-1 and deletion flag. Fourteen cases enter the busy loop
and receive a synthetic releasing update on the second poll. List teardown,
lock destruction and free are intercepted. It verifies main-invoker clearing
before the wait, optional-invoker clearing afterward, helper arguments and
return-stack balance. Negative count alone does not keep this local loop busy.

The runnable [bounded trace model](../../engine/scheduler_job_teardown.py)
accepts supplied state/count read pairs. Exhausting observations while busy
reports an incomplete trace. It never invents a completed drain or runs native
cleanup. For example:

```python
from engine.scheduler_job_teardown import teardown_trace
trace = teardown_trace(True, [(1, 0), (0, 1), (0, 0)])
assert trace['completed']
```

For modding, this rules out treating destructor entry as a general callback
quiescence point. The main invoker is already cleared when the optional wait
starts; the local dispatch reads that invoker unconditionally. The inspected
paths therefore require an external lifecycle/order guarantee to prevent a
concurrent dispatch from consuming the cleared descriptor. The wait itself uses
two separate reads and a flag that starts disabled. Neither that loop nor a zero
counter proves that all mod callbacks, cached pointers or queued work are gone.
We have not established the protecting scheduler phase or enabled-flag writer.

## Separate post-service delegate

The same live graphics table's slot +0x58 targets RVA `0x67adf0`. It acquires
job +8, calls `0x11d16f0`, releases job +8, then conditionally invokes the delegate
at job +0x150 using the same function/context eligibility and tag masking rules.
The inner routine itself acquires and releases job +8. If state +0x54 equals 1,
it calls `0x11e7940` with the global service and job; otherwise it writes state 2.
The locks' implementation and the helper's full effects are outside this local
inspection. Do not call the +0x150 delegate an all-work-finished or unload-safe
callback based on its position after this service. Its scheduling caller and
relationship to active callbacks still need qualification.

## Submission enables the teardown wait

The writer at RVA `0x11e2d06` belongs to the submission routine `0x11e2ca0`,
whose request/begin behavior is already reconstructed in
[MixedScheduler](../../engine/mixed_scheduler.py) and the
[request reducers](REQUEST_STATE_MODEL.md). This closes the previous unknown
writer relationship for this submission path:

```text
submit(job):
    capture_notification_generation()
    lock(job + 8)
    if job.state == UNSCHEDULED:
        job.requested += 1
        if job.holds == 0: job.virtual_begin()
    scheduled = job.state == SCHEDULED  // reread after possible begin
    job.byte_194 = 1
    unlock(job + 8)
    service_notification_generation()
    return scheduled
```

Profiling calls surround this body under a separate global switch. The wait flag
is set even when no request is incremented, and even when a synchronous empty
begin returns the job to UNSCHEDULED. It is set after the virtual begin returns.
The native comparison precedes the flag store; the saved boolean is returned
after unlocking and notification service. The [18-case instruction check](../../native/snow_host/submit_lifetime_validation.json)
varies initial states, holds and begin-result states. It checks the write order,
request count and returned boolean with profiling disabled and external services
intercepted. This identifies one writer, not every submission path or flag reset.

`MixedScheduler` already represented this flag as `usage`; no new native flag is
invented. Its new `teardown_wait_status(name)` connects that existing field to
the destructor predicate and reports state and outstanding dispatches separately
from executions. It is read-only and does not destroy a job. Integration tests
cover queued state with no dispatch yet, callback return before final dispatch
accounting, final drain, immediate empty-range completion and later resubmission.
A false `would_wait` result is an instantaneous serial observation, not a permit
to unload, mutate native descriptors or prevent future requests.

## Queue removal behind the post-service path

The previously opaque helper `0x11e7940` chooses a category queue from job +0x40.
When the low 32-bit affinity mask at +0x38 is nonzero, its least significant set
bit selects an entry in service +0x6c0. A nonnull entry selects that worker's
queue at `worker +0xd0 + category*0x240`. Otherwise the route falls back to
`service + category*0x240`. The category is sign-extended; valid category bounds
are a caller invariant, not checked here.

Under the selected queue lock, helper `0xe30420` searches the pointer array at
queue +0x30 for this job. If found, `0x115b920` shifts the following entries down
and decrements the count, preserving their order. A miss leaves the array alone.
The caller ignores that helper's success byte. If job byte +0x170 is nonzero,
it decrements service +0x8dc regardless of whether removal succeeded. It then
sets job state to DONE and unlocks the queue. Queue membership and accounting
consistency are therefore required invariants, not repaired by this routine.

This is static inspection, not a connected emulation of the removal chain.
The ordinary begin path already called this operation `remove_from_queue`;
see [begin paths](SCHEDULER_BEGIN_PATHS.md). The new connection is to graphics
slot +0x58 through `0x11d16f0`. That route can transition to DONE without waiting
for every outstanding dispatch. Its optional +0x150 delegate must not be exposed
as an all-dispatches-drained notification. The reservation caller is resolved in the section below. Outer lifecycle
exclusion remains open.

## Dispatch phases versus finalization

The worker wrapper at RVA `0x11e9990` invokes job slot +0x40 at `0x11e9a3c`,
restores its execution context, then calls `0x11e2d70` at `0x11e9a7d`. The
[category worker analysis](INPUT_TO_ACTION_ROUTE.md#category-worker-return-and-dependency-release)
already established that wrapper's ordinary completion path. The concrete
graphics binding now connects its before/main/after calls to the same boundary.

The [64-case connected check](../../native/snow_host/graphics_completion_validation.json)
executes the graphics dispatcher, common invoker, completion routine and ordinary
finalizer in that serial order. An authored caller omits the wrapper's TLS,
profiling and notification operations. Synthetic callbacks, lock services and
dependency release replace external effects. The check varies context tags,
optional handlers, states SCHEDULED/DONE and one/two active dispatches. These
supplied states exercise local branches, not asserted live graphics workloads.

All optional after calls run with execution and outstanding counts unchanged.
Completion first decrements executions. With DONE and zero executions, it calls
the ordinary finalizer. That finalizer releases active dependencies before
writing UNSCHEDULED. The outstanding count remains positive during that release
and drops only afterward. With SCHEDULED and the callback job's false empty
predicate, this local completion path does not finalize it. This connects the
callbacks to existing completion semantics without treating an after callback,
DONE state or dependency release as a universal drain.

## Reconstructed before and after handlers

`MixedScheduler` callback definitions accept optional `before_handler` and
`after_handler` names alongside `handler`. Names resolve through the existing
versioned registry. Each receives `(context, None)` and runs synchronously in
before/main/after order, inside the reserved dispatch. Return values do not
select a branch. Missing optional handlers are skipped; an absent main handler
remains the reconstruction's authored no-op fixture policy. This is not a model
of a null native main invoker, which the inspected dispatcher calls unconditionally.

Run the example with:

```sh
python3 -m engine.examples.callback_phase_probe
```

The example reports positive outstanding accounting during all three handlers
and after their return, then zero after `finish_dispatch`. A dependent terminal
job begins during finalization. The registry is immutable after construction;
this API does not replace live native descriptors. Existing fail-stop behavior
on Python handler exceptions is adapter policy, not recovered native unwinding.
Three tests cover ordering and dependency timing, ignored return values, failure
without invented completion, and rejected bindings/job kinds.

A scoped search of indirect slot +0x58 calls in scheduler-region functions found
several profiling and unrelated object calls, but no newly qualified graphics-job
caller. Do not identify those solely from their slot offset. The reservation caller is resolved below. Outer destruction exclusion remains
open.

## Reservation callback and category lock ownership

The selected-job tail at RVA `0x11d8238` increments outstanding dispatches at
+0x50 and executions at +0x4c, then invokes slot +0x58 at `0x11d8246`.
Only afterward does it release the category queue lock. With the observed
ordinary graphics table, that slot is `0x67adf0`, the previously described
post-service delegate path. Thus its +0x150 delegate is the optional reservation
callback, not a completion notification. This connects the concrete binding to
[the already documented callback reservation route](ENGINE_LOOP_HANDSHAKE.md#callback-jobs-become-done-on-reservation).
The earlier unresolved-caller statements are superseded for this queue route.

```text
selected_job_tail(job, category_queue):  // category lock already held
    atomic_increment(job.outstanding_dispatches)
    atomic_increment(job.executions)
    job.on_reservation():
        lock(job)
        lock(job)  // nested state-service call
        if job.state == SCHEDULED:
            remove_from_queue_and_mark_done(job)
        else:
            job.state = DONE
        unlock(job)
        unlock(job)
        invoke_optional_reservation_delegate(job)
    unlock(category_queue)
    return job
```

The removal helper has its own queue locking, described above. The pseudocode
abbreviates that helper and does not claim the queue selected by removal always
aliases the outer category container. Valid routing and lock implementation are
separate native invariants. The reservation delegate runs after the two local
job-lock acquisitions have been released, but before the outer queue unlock.
Earlier wording that merely said "after lock release" was insufficient for
choosing a mod execution phase.

An [eight-case connected instruction check](../../native/snow_host/graphics_reservation_validation.json)
executes the selected tail, concrete reservation method, nested state service,
graphics body dispatcher, common invoker, completion and ordinary finalizer.
All four context tags and optional reservation presence are tested. The category
lock is supplied as held on entry; lock services, removal/state change and
dependency release are intercepted. The fixture observes:

```text
account dispatch -> mark DONE -> optional reservation -> outer queue unlock
-> before -> main -> after -> dependency release -> final accounting return
```

Counts are one during reservation and all body phases. Dependency release sees
zero executions and one outstanding dispatch. The final state has both counts
zero and is UNSCHEDULED. This is serial instruction evidence, not live concurrent
lock validation. A scoped search initially missed the connection because the
selected tail has a separate function-table range and no local state +0x54
access; searches requiring both properties in one range exclude this caller.

The reconstruction now accepts `reservation_handler` for callback jobs, resolved
through the same versioned registry. `reserve(..., context=...)` supplies the
context; `dispatch_next(context)` forwards it. The handler runs after the
reconstructed job becomes DONE and leaves the queue, before reserve returns.
Its trace labels the native lock context. The Python scheduler does not implement
those native locks, and this field is not authorization to install an arbitrary
mod callback under a game queue lock. Keep reservation separate from body-phase
hooks. Failure uses the existing authored fail-stop policy without pretending
the reserved dispatch completed. Three tests cover phase order and counters,
context forwarding, failed reservation and incompatible job kinds. The runnable
`callback_phase_probe` now includes reservation as its first observation.
