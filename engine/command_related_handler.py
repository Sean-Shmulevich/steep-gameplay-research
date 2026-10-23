"""Recovered related-record reference replacement and downstream pool admission.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, related handler and request pool.
Serial caller-owned state; release, initialization and publication are adapters.
No native locks, object lifetime permission or completion semantics are supplied.
"""


def replace_related_reference(entry, holders, *, release, submit):
    """Replace retained with source using the original retain/exchange order.

    entry has source/retained holder identities. Each holder has uint32 status
    and opaque payload. release(identity) represents the low-24-bit-zero helper.
    submit(payload) represents the later request service; its result is exposed
    diagnostically here, although the original handler does not test it.
    TLS reads between replacement and submission have no modeled side effects.
    """
    source = entry['source']

    def change(identity, delta):
        value = holders[identity]['status']
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError('uint32 holder status required')
        holders[identity]['status'] = value = (value + delta) & 0xffffffff
        if delta == -1 and value & 0xffffff == 0:
            release(identity)

    change(source, 1)
    change(source, 1)
    old = entry['retained']
    entry['retained'] = source
    change(old, -1)
    change(source, -1)
    # Native code reloads source after reference-service callbacks.
    result = submit(holders[entry['source']]['payload'])
    return dict(submission_result=result, original_tests_submission_result=False,
                native_receiver_retention_proved=False)


def admit_pooled_request(pool, *, initialize, publish):
    """Model the downstream request-pool branch, outside its native lock services.

    pool: slots, count, read_index, capacity, available_total (uint32).
    initialize(record) then publish(record) run after the native pool-lock release.
    Positive count with a null slot consumes the slot/accounting and returns false.
    Successful return means local initialization/publication calls returned, not
    that downstream work completed. Their bodies and exceptions remain external.
    """
    count = pool['count']
    if type(count) is not int or not 0 <= count <= 0xffffffff:
        raise ValueError('uint32 count required')
    if count == 0 or count & 0x80000000:
        return False
    capacity, index = pool['capacity'], pool['read_index']
    if type(capacity) is not int or capacity <= 0 or type(index) is not int or not 0 <= index < capacity:
        raise ValueError('valid supplied ring required')
    record = pool['slots'][index]
    pool['read_index'] = (index + 1) % capacity
    pool['count'] = count - 1
    pool['available_total'] = (pool['available_total'] - 1) & 0xffffffff
    if record is None:
        return False
    initialize(record)
    publish(record)
    return True
