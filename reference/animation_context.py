"""Evaluator context-holder exchange, serialized arithmetic only.

Evidence: CENTRAL_IMPULSE.md, Evaluator context retention boundary.
Models the observed atomic operation order without providing synchronization.
Holder retirement is an opaque service; token lifetime is not established.
"""


def exchange_holder(new_count, old_count, new_status, old_status, alias=False):
    for value in (new_count, old_count, new_status, old_status):
        if type(value) is not int or not 0 <= value < 2**32:
            raise ValueError('uint32 holder field required')
    if type(alias) is not bool:
        raise ValueError('boolean alias required')
    if alias and (new_count != old_count or new_status != old_status):
        raise ValueError('aliased holder state must agree')
    counts = {'new': new_count, 'old': old_count}
    counts['new'] = (counts['new'] + 2) & 0xffffffff
    if alias:
        counts['old'] = counts['new']
    retired = []
    before = counts['old']
    counts['old'] = (before - 1) & 0xffffffff
    if alias:
        counts['new'] = counts['old']
    if before == 1 and old_status & 0xffffff == 0:
        retired.append('shared' if alias else 'old')
    before = counts['new']
    counts['new'] = (before - 1) & 0xffffffff
    if alias:
        counts['old'] = counts['new']
    if before == 1 and new_status & 0xffffff == 0:
        retired.append('shared' if alias else 'new')
    return dict(new_count=counts['new'], old_count=counts['old'], retired=retired)
