"""Recovered request-consumer callback routing and normal retirement ordering.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, request consumer and callback gates.
Caller supplies owned state and opaque services. Native thread context, request
production, cancellation and allocator cleanup remain outside this serial model.
"""


def consume_requests(manager, *, services, max_iterations=4096):
    """Run the consumer with active requests supplied by acquire_active.

    manager has stop and active. Work has kind, descriptor, resource, seed,
    payload, mode, associated, reload, callback and context. resource/descriptor
    represent resolved holder pointees; their ownership is external. Callback
    receives code, associated, work (for both holder-field addresses), context.
    It must resolve those fields through work rather than a copied snapshot.
    services provide reset_event, prepare, acquire_active, descriptor_ready,
    defer, materialize, release_seed, alternate, lock, recycle, unlock, signal.
    """
    if type(max_iterations) is not int or max_iterations < 1:
        raise ValueError('positive authored iteration limit required')
    services['reset_event']()
    iterations = callbacks = 0
    if manager['stop']:
        return dict(iterations=0, callbacks=0, native_drain_proved=False)
    while True:
        if iterations == max_iterations:
            raise RuntimeError('authored request iteration limit exhausted')
        iterations += 1
        services['prepare'](manager)
        services['acquire_active'](manager)
        work = manager['active']
        if work is None:
            services['signal']()
            break
        if work['kind'] != 0:
            services['alternate'](work['context'])
        elif work['descriptor'] is not None and not services['descriptor_ready'](work['descriptor']):
            services['defer'](manager['active'])
        else:
            work = manager['active']
            if work['resource'] is None:
                services['materialize'](work, False)
                code = 1
            elif work['reload']:
                services['materialize'](work, True)
                code = 2
            else:
                if work['seed'] is not None:
                    services['release_seed'](work['seed'])
                code = 0
            work = manager['active']
            if work['resource'] is not None and work['callback'] is not None:
                work['callback'](code, work['associated'], work, work['context'])
                callbacks += 1
        services['lock']()
        retiring = manager['active']
        manager['active'] = None
        services['recycle'](manager, retiring)
        services['unlock']()
        services['signal']()
        if manager['stop']:
            break
    return dict(iterations=iterations, callbacks=callbacks, native_drain_proved=False)
