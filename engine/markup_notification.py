"""Recovered local markup notification decision, not a clip/graph evaluator.

See CENTRAL_IMPULSE.md, Markup dispatch and callback argument contract.
Sampled values come from external graph predicates. Listener dispatch, allocation,
reentrancy and scheduling remain external to this local record update.
"""

def advance_markup_record(link_count, previous_value, sampled_value, force_flag, pending_index):
    """Return the local decision and cache writes for one markup record.

    Bytes retain their raw values. A nonpositive signed link count skips querying
    and leaves both cache fields unchanged; sampled_value may be None then.
    """
    for value in (link_count,pending_index):
        if type(value) is not int or not -(2**31) <= value < 2**31:
            raise ValueError('count and pending index must be int32')
    for value in (previous_value,force_flag):
        if type(value) is not int or not 0 <= value <= 255:
            raise ValueError('cache and force flag must be bytes')
    if link_count <= 0:
        return dict(evaluated=False,notify=False,previous_value=previous_value,pending_index=pending_index)
    if type(sampled_value) is not int or not 0 <= sampled_value <= 255:
        raise ValueError('linked record requires a sampled byte')
    notify=sampled_value!=previous_value or (force_flag!=0 and pending_index!=-1)
    return dict(evaluated=True,notify=notify,previous_value=sampled_value,pending_index=-1)
