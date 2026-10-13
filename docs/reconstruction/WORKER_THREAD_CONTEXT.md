# Worker thread context and execution-wrapper mode

A focused static pass joins the ordinary worker-loop writer to the context slot
read by [explicit helping](WAIT_HELPER_DISPATCH.md). It also identifies the job
mode field previously left neutral in [AI queue assignments](AI_QUEUE_ASSIGNMENTS.md).
These are local TLS and wrapper relationships, not a safe external-thread API.

## Context producer and helper lookup

At entry, the ordinary worker loop obtains the module's thread-local block and
stores its worker receiver in the scheduler-context slot. Later ordinary dispatch
passes that same worker receiver directly to the execution wrapper. The helper
obtains the same module TLS block and passes the pointer stored in that slot.
The helper retains the slot address and reloads its pointer for each invocation.

```text
ordinary_worker_loop(worker):
    tls.scheduler_context = worker
    wait_adapter(worker.event_holder)
    while worker.run_flag:
        job = select_and_reserve_work_or_wait(worker)
        if job != null:
            execute_wrapper(worker, job)
    notify_worker_exit()

help_specific_job(job):
    slot = address_of(tls.scheduler_context)
    while not job.is_empty():
        increment_dispatch_accounting(job)
        execute_wrapper(slot.value, job)
    inspect_state_and_outstanding_until_wait_condition()
```

Names of the wait and exit helpers describe their role in the control flow;
exact platform operations remain separately unverified. The decoded worker-loop
return path does not clear this TLS slot locally. It does not follow that stale
TLS escapes thread destruction: thread lifetime and external cleanup remain open.

## Mode save and restore

The job mode read by the wrapper is the same field written by the small setter
that conditionally clears excluded masks. The base constructor initializes it to
255. Setup calls supplying zero therefore select a temporary execution mode;
they do not change queue category.

```text
execute_wrapper(context_argument, job):
    begin_optional_diagnostic_scope(job)
    saved_mode = 255
    if job.mode != 255:
        saved_mode = tls.execution_mode
        tls.execution_mode = job.mode

    if tls.scheduler_context != null:
        context_argument.before_job()
    job.worker_body()
    if tls.scheduler_context != null:
        context_argument.after_job()

    if job.mode != 255:
        tls.execution_mode = saved_mode
    end_optional_diagnostic_scope(job)
    before = queue_manager.change_counter
    complete_job_accounting(job)
    if queue_manager.change_counter != before:
        notify_workers()
```

The two context hooks are distinct virtual slots. Their concrete implementations for the inspected worker initializer are now
resolved below; the called service operation remains semantically unnamed. The condition checks TLS, while the
call receiver is the separately supplied context argument. Correct agreement of
those values is a caller/context invariant. The ordinary loop and helper provide
concrete matching routes at their call boundaries; changes inside callbacks are
not ruled out.

The restore decision rereads the job mode. A mutation to or from sentinel 255
during execution can change restoration behavior. No such mutation is observed,
and the independent adapter should not silently promise a stronger native scope
guarantee. Exception cleanup is outside this normal-return decode.

## What null context establishes

A null TLS scheduler-context value skips the wrapper's two context hooks. It does
not skip the concrete worker body or prove that body is thread-independent. Other
TLS fields, locks, job-type protocols and owner lifetime can still be required.
Therefore the previous native-thread-context release gate remains open. No
external thread should call this wrapper based only on the null branch.

## Verification and next targets

The ordinary worker loop, full explicit helper and full execution wrapper were
decoded from image SHA-256
`32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`.
The module TLS index and slot offsets match across the three routines. No game
execution, thread injection or TLS write was performed.

Next: resolve the worker table's before/after hooks and the execution-mode readers.
The independent helper ID remains an explicit context label, not a native worker
pointer or proof that native context initialization has been reproduced.

## Concrete worker hooks

The worker initializer allocates a worker, runs its base constructor, then installs
a concrete table and clears a byte-sized per-worker latch. The before/after slots
used by the execution wrapper resolve through that exact table, establishing this
behavior for those initialized workers:

```text
before_job(worker):
    if worker.service_latch:
        return
    service = global_service
    if service == null:
        return
    if not service.enabled_predicate():
        return
    service.worker_operation()
    worker.service_latch = true

after_job(worker):
    return
```

The service receiver is loaded from a global pointer. The operation receives that
service receiver, not the worker pointer, in its ordinary argument register. Its
implementation may consult TLS, but this pass does not establish that. The two
service calls use different virtual slots. The latch is set only after the second
call returns normally.

This is a retryable one-time hook: absent or disabled service leaves the latch
false and a later job retries. Once the operation returns and sets the latch,
subsequent before hooks skip the service. The concrete after hook returns without
undoing that state or calling the service. This sequence does not support calling
the hooks a per-job lock/unlock pair.

The initializer's latch-zero store and concrete table assignment were checked
against the same image. Later latch-reset writers, replacement worker tables and
the global service's assignment/implementation remain open. These hooks do not
close the requirements of arbitrary job bodies or prove a new thread is safe for
native helping.

The next useful native target is the global service producer and its two virtual
implementations, followed by readers of the separate TLS execution mode. The
one-time hook can be represented independently without inventing those service
semantics, but calling a placeholder service is not original-runtime equivalence.

## Service factory and callback dispatch

A follow-up finds a global-service writer that calls a factory and stores its
returned pointer. The factory allocates an eight-byte object, installs a concrete
table, performs an additional registration call and returns the object. A local
null-allocation branch returns null. The registration operation's wider role and
service destruction are not established here.

Through the installed table, the enabled predicate reads one global byte and
returns it. The worker operation follows two unconditional jump adapters into a
callback-array visitor:

```text
service.enabled_predicate():
    return global_enabled_byte

service.worker_operation():
    index = uint32(0)
    while index < unsigned(global_callback_count):
        callback = global_callback_table[index]
        callback(0)
        index = uint32(index + 1)
```

The count is read before entry and again after each call, rather than captured as
an immutable bound. Each callback receives zero in its first integer argument.
No job or worker pointer is passed explicitly through that argument. Individual
callbacks may consult TLS or globals; their identities and semantics still require
producer/registration tracing.

Combining this with the worker latch means absent or disabled service retries on
later jobs. When enabled, an empty callback table still returns normally and sets
the worker latch. Callbacks registered only afterward therefore are not guaranteed
to run through that same worker hook, absent a later latch reset or another entry.
The loop's count reread also prevents claiming a fixed callback snapshot during a
concurrent registration or callback-induced change. No mutation safety contract is
inferred from that reread.

Another function references the same table during a separate callback-entry path;
its full protocol remains open. The current evidence closes the concrete service
and its loop, but not the registration writers, table lifetime, callback meanings
or exception behavior. The image hash and no-live-execution boundary above apply.

## Shared callback protocol at thread entry

The other callback-table reference resolves to an entry wrapper supplied as a
function argument to a protected thread-creation-shaped adapter. Exact platform
API identity remains unresolved. Its own ordinary instructions are decoded:

```text
entry_wrapper(descriptor):
    body = descriptor.body
    argument = descriptor.argument
    notify_callbacks = descriptor.notify_callbacks
    descriptor.started = true
    if notify_callbacks:
        visit_global_callbacks_with_live_count(1)
    body(argument)
    if notify_callbacks:
        visit_global_callbacks_with_live_count(3)
    return 0
```

Both callback walks use the same table/count as the scheduler service's
argument-zero walk. The entry and exit walks each start at index zero and reread
the global count after callbacks. These are established stage codes and ordering;
formal enum names, registration writers and individual callback behavior are not
recovered. The table now has a concrete thread-lifecycle relationship, rather than
an unclassified worker-only service association.

The descriptor fields needed afterward are copied to registers before `started`
is set. The surrounding creation-shaped function passes a temporary descriptor and
later polls that byte. This is consistent with a descriptor-consumption handshake,
not proof that callback initialization has completed. Protected calls in that
surrounding function prevent claiming the full OS thread-start protocol or memory
ordering from this local sequence alone.

In particular, `started == true` can coexist with entry callbacks still running,
the supplied body not yet entered, and the scheduler worker's separate one-time
hook not yet reached. The scheduler hook's mode zero is not interchangeable with
the entry wrapper's mode one. Exit mode three occurs after ordinary body return;
exception unwinding, forced termination and callback failure remain outside this
normal-return analysis.

The stored count and first inspected table entries are zero in the analyzed image.
That is not a live registration inventory. The bounded direct writer search did
not locate a population path, so callback identities remain an explicit missing
producer. No native callback is supplied or emulated in the independent runtime.


## Idle and notification counter protocol

Static inspection joins the ordinary worker's idle decrement to the notification
CAS in the execution wrapper. The counter is signed 32-bit storage. The following
names describe local roles, not recovered type names:

```text
# After selection found no job, or a separate worker gate bypassed selection:
if worker.run_flag == 1:
    old = atomic_fetch_add(worker.notification_counter, -1)
    if int32_wrap(old - 1) < 0:
        atomic_increment(global_waiting_counter)
        wait_adapter(worker.event_holder)
        atomic_decrement(global_waiting_counter)
# Return to the run-flag check and selection loop.

# After job accounting changed the queue generation, for each worker:
repeat:
    old = load(worker.notification_counter)
    proposed = min_signed(int32_wrap(old + 1), 1)
until compare_exchange(worker.notification_counter, old, proposed) succeeds
if old < 0:
    notify_adapter(worker.event_holder)
```

The idle instruction sequence uses fetch-add minus one, then CMP against one and
JNS on the returned old value. Therefore its exact condition is the sign of the
wrapped subtraction. It must not be rewritten as a signed old-less-than-one test
at the minimum int32 value. That extreme has no established runtime reachability.
The notifier's increment also wraps before its signed minimum operation.

For the ordinary values, a notification before the idle decrement changes zero to
one, allowing the worker to consume a retry without entering the wait adapter.
Repeated notifications saturate at one. If idle decrements zero to minus one
first, notification changes minus one to zero and calls the event adapter. The
latter can happen before the worker actually enters its wait call. Avoiding a lost
wakeup in that interval requires event behavior that retains or otherwise safely
coordinates the notification. The counter alone does not prove that property.

The wait adapter dereferences the event holder and supplies an all-ones second
integer argument before entering protected code. The notify adapter dereferences
the holder before another protected call. These call shapes are consistent with
an indefinite wait and signaling, but exact APIs, return handling, reset policy
and failure behavior remain unresolved. No OS event semantics are emulated here.
The ordinary worker also calls the wait adapter once before its first run-flag
check, independently of the idle-counter branch.

The global waiting counter brackets adapter entry and normal return. It does not
prove a thread has entered an OS wait, that all workers are stopped, or that
submissions are excluded. A separate worker byte bypasses queue selection; its
producer and meaning remain open. The loop tests run_flag equal to one inside the
selection path but nonzero after execution. Noncanonical flag values therefore
must not be normalized silently.

[The pure transition helpers](../../engine/worker_notification.py) preserve these
counter operations at a successful atomic-operation boundary. Their tests cover
both notification/idle orderings, notification coalescing, overflow and input
validation. They do not implement CAS contention, native events, thread parking
or a safe scheduler pause. The serial mixed scheduler remains independent of OS
worker wakeups.


## Construction and worker entry ordering

The worker base constructor sets the selection-bypass byte to zero, run flag to
one, notification counter to zero and configured mode to 255. The zero counter
comes from the exhausted three-iteration category construction loop. Event-holder
construction receives two boolean arguments, false and true. Its visible adapter
maps these to four platform-call arguments:

```text
platform_create(0, not second_boolean, first_boolean, 0)
# For this worker: platform_create(0, 0, 0, 0).
worker.event_holder = returned_handle
```

The argument shape is compatible with an initially unsignaled auto-reset event,
but the protected target has not been identified. That interpretation remains a
lead, not a recovered event contract. The visible adapter stores the result
without a local null check. Failure handling may exist elsewhere.

The concrete worker table uses the same outer entry and loop as the base table,
but overrides startup and exit hooks. Startup adds diagnostic scope around the
base hook. Ignoring those optional diagnostic calls, ordinary entry is:

```text
worker_entry(worker):
    tls.execution_mode = worker.configured_mode
    thread_context_adapter(worker)
    worker.startup_hook():
        tls.worker_index = worker.configured_index
        tls.secondary_mode = 6
        tls.execution_mode = 6
        register_worker(queue_manager, worker)
    startup_notification_adapter(shared_startup_holder)
    worker.loop():
        tls.scheduler_context = worker
        wait_adapter(worker.event_holder)
        run_selection_and_execution_loop()
        notify_adapter(shared_exit_holder)
    worker.exit_hook()
    count = signed_global_exit_callback_count
    if count > 0:
        visit_that_many_exit_callbacks_without_explicit_arguments(count)
```

The mode write of six is concrete; the meaning of that mode and the secondary TLS
field remains unresolved. A default-mode job leaves this current execution mode
unchanged. An explicitly tagged job temporarily replaces it through the previously
decoded wrapper, subject to its normal-return and mode-stability conditions.
Registration appends the worker pointer to the manager's worker array and increments
a separate manager count. This joins initialization to the array used by the
notification walk. It does not prove concurrent registration is supported.

The startup notification adapter receives the dereferenced holder, integer one
and zero before entering protected code. The setup caller waits on the same
shared holder after its thread-start call. This establishes a concrete shared
handshake path. The notification occurs after registration but before the loop's
scheduler-context TLS assignment and initial wait. Its receipt therefore cannot
prove that the worker has selected work or reached its first job hook. Exact
platform operation and wait failure handling remain open.

## Concrete worker exit hook

The concrete exit override tests the worker's service latch. If it is set, it
calls a separate global indirect target with these explicit arguments:

```text
if worker.service_latch:
    cleanup_callback(address_of_global_cleanup_context,
                     global_cleanup_value & ~3,
                     0)
worker.run_flag = 0
```

The callback target and context values are zero in the analyzed stored image;
that does not describe a live initialized worker. Their writers and callback
semantics remain open. There is no visible latch reset or null-target guard on
this branch. The callback is distinct from the earlier service callback-table
walk; no pairing of individual callback identities is established.

Crucially, this hook runs after the ordinary worker loop returns. Its run-flag
clear is not by itself a stop request that wakes a parked worker. Some preceding
cause must let the loop return. The final exit-callback list is also distinct from
the thread-entry stage table: its signed positive count is captured once, while
the stage-table loops reread their unsigned count. No explicit argument registers
are prepared for these exit callbacks.

The base destructor releases the event holder and local queue storage before
entering the base thread destructor. Whether outer ownership already stopped and
joined the thread remains open. No safe destruction or pause operation follows
from this local cleanup sequence alone.
