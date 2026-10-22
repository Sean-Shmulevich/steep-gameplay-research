"""Recovered ownership release for the ActionKit source-handle array.

Evidence: ACTION_KIT_CACHE.md, Source handles own references.
Retirement and deallocation effects are returned, not executed.
"""
from reference.record_retirement import decrement_ownership_word


def plan_handle_array_cleanup(status_words, slots, storage_flags, storage_present=True):
    if type(storage_flags) is not int or not 0 <= storage_flags < 2**16:
        raise ValueError('uint16 storage flags required')
    if type(storage_present) is not bool or (not storage_present and slots):
        raise ValueError('nonempty slots require storage')
    if len(slots) > 65535:
        raise ValueError('uint16 element count required')
    if any(type(s) is not int or not 0 <= s < 2**32 for s in status_words):
        raise ValueError('uint32 status words required')
    if any(type(s) is not int or not 0 <= s < len(status_words) for s in slots):
        raise ValueError('valid record indices required')
    after = list(status_words)
    effects = []
    if not storage_flags & 0x4000:
        for slot in slots:
            released = decrement_ownership_word(after[slot])
            after[slot] = released['status_word']
            if released['request_retirement']:
                effects.append(dict(kind='request_retirement', record=slot))
    if storage_present and not storage_flags & 0x8000:
        effects.append(dict(kind='free_storage'))
    return dict(status_words=after, effects=effects, descriptor_cleared=False)
