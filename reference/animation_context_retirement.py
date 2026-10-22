"""Recovered context-holder retirement under an externally supplied lock.

See docs/reconstruction/ANIMATION_CONTEXT_RETIREMENT.md. Effect plans do not
execute callbacks, allocator operations, synchronization or pointer writes.
"""

def plan_context_retirement(*, references, status, target_word=None,
                            backing_present=False, backing_in_reserved_range=False,
                            slot_index=None, free_head=None):
    for value in (references, status):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError('uint32 references and status required')
    if target_word is not None and (type(target_word) is not int or not 0 <= target_word <= 0xffffffff):
        raise ValueError('optional uint32 target word required')
    if type(backing_present) is not bool or type(backing_in_reserved_range) is not bool:
        raise ValueError('explicit backing predicates required')
    result=dict(action='gated',references=references,status=status,
                target_word=target_word,target_attached=target_word is not None,
                effects=[],free_head=free_head)
    if status & ((1 << 26) | (1 << 24) | 0xffffff) or references:
        return result
    effects=result['effects']
    if target_word is not None:
        result['target_word']=target_word & 0xfff80000
        if target_word & (1 << 28):
            effects.append('target_service')
        result['target_attached']=False
        status &= ~(1 << 31)
        effects.append('detach_target')
    status |= 1 << 26
    result.update(action='retired',status=status)
    effects.append('mark_retired')
    if backing_present:
        for value in (slot_index,free_head):
            if type(value) is not int or not 0 <= value <= 0xffffffff:
                raise ValueError('uint32 supplied slot index and free head required')
        if not backing_in_reserved_range and not status & (1 << 28):
            effects.append('unregister_backing')
        effects.append('recycle_slot')
        result.update(references=free_head,free_head=slot_index)
    return result
