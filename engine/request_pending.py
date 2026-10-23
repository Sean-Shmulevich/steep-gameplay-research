"""Recovered request publication and four-category pending-to-ready transfer.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, pending publication and ready transfer.
Serial supplied rings with small valid indices/counts; services model lock/event
and seed adapters. This does not establish native thread safety or admission.
"""


def _insert(ring, item):
    if ring['count'] >= ring['capacity']:
        return False
    ring['slots'][ring['write_index']] = item
    ring['count'] += 1
    ring['write_index'] = (ring['write_index'] + 1) % ring['capacity']
    return True


def _pop(ring):
    index = ring['read_index']
    value = ring['slots'][index]
    ring['read_index'] = (index + 1) % ring['capacity']
    ring['count'] -= 1
    return value


def publish_request(manager, work, *, services):
    """Publish into work.mode's category; insertion result is model diagnostics.

    Counters advance even if insertion fails. Wake counter update follows unlock.
    The original publisher does not expose this inserted boolean as a receipt.
    """
    mode, kind = work['mode'], work['kind']
    if type(mode) is not int or not 0 <= mode < 4 or len(manager['pending']) != 4:
        raise ValueError('four categories and mode 0..3 required')
    services['lock']()
    manager['pending_total'] = (manager['pending_total'] + 1) & 0xffffffff
    inserted = _insert(manager['pending'][mode], work)
    if kind == 0:
        manager['normal_outstanding'] = (manager['normal_outstanding'] + 1) & 0xffffffff
    services['unlock']()
    old = manager['wake_counter']
    if type(old) is not int or not -(1 << 31) <= old < (1 << 31):
        raise ValueError('signed int32 wake counter required')
    # This publisher compares OLD against 1 before selecting the increment.
    # Do not reuse a kernel that compares the wrapped increment at INT_MAX.
    notification = dict(counter=1 if old >= 1 else old + 1,
                        call_notify_adapter=old < 0)
    manager['wake_counter'] = notification['counter']
    if notification['call_notify_adapter']:
        services['notify']()
    return dict(inserted=inserted, notification=notification, native_admission_proved=False)


def transfer_pending(manager, *, services, max_pops=4096):
    """Scan categories 0..3, draining each before advancing, subject to seed stop.

    Empty category 1 calls refill while unlocked. A true result rechecks that
    same category. Nonnull pops decrement pending_total even if ready is full.
    Normal work needing a resource or reload calls prepare_seed under the queue
    lock and ends this pass. Preparation happens even if ready insertion failed.
    max_pops is an authored attempt limit, including inconsistent refill retries.
    """
    if len(manager['pending']) != 4 or type(max_pops) is not int or max_pops < 1:
        raise ValueError('four categories and positive attempt limit required')
    services['before_transfer']()
    services['lock']()
    category = attempts = popped = inserted = 0
    seed_prepared = False
    while category < 4:
        if attempts == max_pops:
            raise RuntimeError('authored transfer attempt limit exhausted')
        attempts += 1
        ring = manager['pending'][category]
        if ring['count'] == 0:
            if category == 1:
                services['unlock']()
                refilled = services['refill'](manager)
                services['lock']()
                if refilled:
                    continue
            category += 1
            continue
        if ring['count'] < 0:
            raise ValueError('negative ring count outside supplied domain')
        work = _pop(ring)
        popped += 1
        if work is None:
            continue
        manager['pending_total'] = (manager['pending_total'] - 1) & 0xffffffff
        inserted += int(_insert(manager['ready'], work))
        if work['kind'] == 0 and (work['reload'] or work['resource'] is None):
            services['prepare_seed'](work)
            seed_prepared = True
            break
    services['unlock']()
    return dict(popped=popped, inserted=inserted, seed_prepared=seed_prepared,
                native_request_ownership_proved=False)
