"""Authored serial adapter for the decoded ordinary execution wrapper.

Evidence: WORKER_THREAD_CONTEXT.md (Mode save and restore), SCHEDULER_DELEGATES.md
(completion boundaries). This models normal-return ordering, not OS TLS, native
threads, atomic publication, exception unwinding, or a safe native mod callback.
The caller supplies mutable job/TLS/queue observations and effect callbacks.
"""
from .worker_notification import notify_transition


def _u32(value):
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('expected uint32')
    return value


def execute_worker_wrapper(*, context, job, tls, queue, body, complete,
                           before_job, after_job, diagnostic_begin,
                           diagnostic_end, notify_worker, diagnostic_mode=2):
    """Mutate owned synthetic state and invoke supplied effects in native order.

    job: mode uint32, diagnostic_scope opaque truthy handle or None.
    tls: execution_mode uint32, scheduler_context opaque handle or None.
    queue: change_counter uint32, workers list of {wake_counter: int32}.
    Context-hook gates reread the retained TLS block; hook receiver is the explicit
    context argument. Mode restore rereads job.mode, exactly as inspected. No
    finally-based restoration is invented on callback exceptions. Callers own all
    objects and must serialize them; callback reentrancy/concurrent mutation is
    outside this adapter's contract. A worker notification is not a drain event.
    """
    _u32(job['mode']);_u32(tls['execution_mode']);_u32(queue['change_counter'])
    _u32(diagnostic_mode)
    if type(queue['workers']) is not list:
        raise ValueError('workers must be a list')
    for worker in queue['workers']:
        notify_transition(worker['wake_counter'])  # Validate without mutation.
    events = []
    def event(phase, **values):
        events.append(dict(phase=phase, **values))
    scope = job.get('diagnostic_scope')
    if scope:
        diagnostic_begin(scope if diagnostic_mode == 2 else None)
        event('diagnostic_begin')
    saved_mode = 255
    if _u32(job['mode']) != 255:
        saved_mode = _u32(tls['execution_mode'])
        tls['execution_mode'] = job['mode']
        event('mode_installed', value=job['mode'])
    if tls.get('scheduler_context'):
        before_job(context);event('context_before')
    body(job);event('body_return')
    if tls.get('scheduler_context'):
        after_job(context);event('context_after')
    if _u32(job['mode']) != 255:
        tls['execution_mode'] = saved_mode
        event('mode_restored', value=saved_mode)
    if scope:
        diagnostic_end();event('diagnostic_end')
    captured = _u32(queue['change_counter'])
    event('completion_enter', queue_change=captured)
    complete(job)
    observed = _u32(queue['change_counter'])
    event('completion_return', queue_change=observed)
    if observed != captured:
        # The native loop retains its worker-array bounds. The supplied owned
        # collection is stable during this operation; each wake value is read
        # when visited. This is not a model of CAS retries under contention.
        for index, worker in enumerate(queue['workers']):
            previous = worker['wake_counter']
            result = notify_transition(previous)
            worker['wake_counter'] = result['counter']
            event('worker_counter_updated', worker=index, previous=previous,
                  value=result['counter'])
            if result['call_notify_adapter']:
                notify_worker(index);event('worker_notified', worker=index)
    event('wrapper_return')
    return dict(events=events, queue_changed=observed != captured,
                native_thread_context_established=False, global_drain_proved=False)
