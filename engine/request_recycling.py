"""Recovered normal work-record reset and free-pool return ordering.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, request recycling and context clearing.
Owned serial objects and supplied services; native allocation, holder ownership,
locks, cancellation and actual context freeing remain outside this model.
"""


def reset_request(work, holders, *, default_holder, services):
    """Reset request fields without inventing destruction of callback context.

    work has payload, resource_holder, descriptor_holder, callback, alternate,
    context, associated, marked, reload, tracked, kind, mode and seed.
    Holder status is uint32. Services handle zero-count release, associated-field
    clearing, seed allocation query/destruction/free. No callback is invoked.
    """
    work['payload'] = None
    for field in ('resource_holder', 'descriptor_holder'):
        identity = work[field]
        status = holders[identity]['status']
        if type(status) is not int or not 0 <= status <= 0xffffffff:
            raise ValueError('uint32 holder status required')
        status = (status - 1) & 0xffffffff
        holders[identity]['status'] = status
        if status & 0xffffff == 0:
            services['release_holder'](identity)
        work[field] = default_holder
    work['callback'] = None
    work['alternate'] = None
    work['marked'] = False
    work['context'] = None
    work['mode'] = 1
    services['clear_associated'](work)
    work['reload'] = False
    work['tracked'] = False
    work['kind'] = 1
    seed = work['seed']
    if seed is not None:
        token = services['allocation_token'](seed)
        services['destroy_seed'](seed)
        services['free_seed'](seed, token)
    work['seed'] = None


def recycle_request(pool, work, *, reset, services):
    """Return a reset work record using the captured pre-reset kind.

    pool contains slots, capacity, count, write_index, available_total and
    normal_outstanding. Caller supplies valid small nonnegative ring counters.
    Lock services bracket the pool write; caller may already hold the same lock.
    Counter increments occur even when the free ring has no room for insertion.
    reset and unlink_tracking are supplied adapters for the earlier native calls.
    """
    kind = work['kind']
    payload = work['payload']
    if work['tracked']:
        services['unlink_tracking'](payload)
    reset(work)
    services['lock']()
    inserted = pool['count'] < pool['capacity']
    if inserted:
        pool['slots'][pool['write_index']] = work
        pool['count'] += 1
        pool['write_index'] = (pool['write_index'] + 1) % pool['capacity']
    pool['available_total'] = (pool['available_total'] + 1) & 0xffffffff
    if kind == 0:
        pool['normal_outstanding'] = (pool['normal_outstanding'] - 1) & 0xffffffff
    services['unlock']()
    return dict(inserted=inserted, native_context_free_proved=False)
