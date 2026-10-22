"""Recovered retirement-queue dispatch, with opaque cleanup effects explicit.

Evidence: docs/reconstruction/CENTRAL_IMPULSE.md, Retirement queue ownership gate.
This is an effect plan for a popped record, not a lifetime-acquisition API.
"""


def plan_retirement(status_word, object_present, pool_mode):
    """Plan serial queue-consumer actions from the status at the pop boundary.

    Cleanup can change the record. The clear operation therefore names a mask
    to apply to the *current* status after cleanup; no final status is predicted.
    Record +8 count is deliberately absent: this dispatch does not inspect it.
    """
    if any(type(v) is not int or not 0 <= v < 2**32 for v in (status_word, pool_mode)):
        raise ValueError('uint32 status and pool mode required')
    if type(object_present) is not bool:
        raise ValueError('object_present must be bool')
    effects = []
    if status_word & 0xffffff == 0:
        if object_present:
            effects.append('object_cleanup')
            effects.append('schedule_object_disposal' if pool_mode == 0 else 'append_object_to_disposal_list')
        effects.extend(['clear_queued_bit', 'record_reclaim'])
    else:
        effects.append('clear_queued_bit')
    return dict(effects=effects, clear_status_mask=0xfeffffff,
                ownership_count=status_word & 0xffffff,
                lifetime_acquisition_proven=False)


def increment_ownership_word(status_word):
    """Model the original whole-word increment, not safe lifetime acquisition.

    The inspected lookup wrapper performs this inside the pool lock. The actual
    operation increments all 32 bits; saturation of the low 24 bits is not checked.
    Caller validity, registry lookup and lock acquisition are not modeled here.
    """
    if type(status_word) is not int or not 0 <= status_word < 2**32:
        raise ValueError('uint32 status required')
    after = (status_word + 1) & 0xffffffff
    return dict(status_word=after, ownership_count=after & 0xffffff,
                ownership_overflow=(status_word & 0xffffff) == 0xffffff,
                lifetime_acquisition_proven=False)


def decrement_ownership_word(status_word):
    """Model paired release arithmetic and its retirement-request predicate.

    A request is emitted when the resulting low 24 bits are zero. It is not
    proof of object destruction or record reclamation. Like the original,
    arithmetic wraps the entire uint32 word without an underflow guard.
    """
    if type(status_word) is not int or not 0 <= status_word < 2**32:
        raise ValueError('uint32 status required')
    after = (status_word - 1) & 0xffffffff
    return dict(status_word=after, ownership_count=after & 0xffffff,
                ownership_underflow=(status_word & 0xffffff) == 0,
                request_retirement=(after & 0xffffff) == 0)


def assign_owned_record(status_words, old_record, new_record):
    """Model lookup-temporary acquisition, slot assignment and temporary release.

    Indices identify records, so aliasing old/new preserves the native operation
    order. Lookup and retirement effects are not executed. The caller must already
    have established which record lookup returns.
    """
    if any(type(v) is not int or not 0 <= v < 2**32 for v in status_words):
        raise ValueError('uint32 statuses required')
    if any(type(i) is not int or not 0 <= i < len(status_words) for i in (old_record, new_record)):
        raise ValueError('valid record indices required')
    after = list(status_words)
    after[new_record] = increment_ownership_word(after[new_record])['status_word']
    after[new_record] = increment_ownership_word(after[new_record])['status_word']
    retire = []
    for index in (old_record, new_record):
        release = decrement_ownership_word(after[index])
        after[index] = release['status_word']
        if release['request_retirement']:
            retire.append(index)
    return dict(status_words=after, slot_record=new_record, retirement_requests=retire)
