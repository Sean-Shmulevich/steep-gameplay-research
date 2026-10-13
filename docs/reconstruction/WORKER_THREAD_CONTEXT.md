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

The two context hooks are distinct virtual slots. Their implementations and
semantic purpose are not established here. The condition checks TLS, while the
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
