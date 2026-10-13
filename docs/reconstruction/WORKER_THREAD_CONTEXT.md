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
    initialize_worker_wait_state()
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

Names of the wait-state and exit helpers describe their role in the control flow;
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
        global_callback_table[index](0)
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
