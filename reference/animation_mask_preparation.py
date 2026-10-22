"""Recovered blend-mask byte scatter before masked pose blending.

Evidence: CENTRAL_IMPULSE.md, Blend-mask byte preparation.
Descriptors/indices are immutable metadata in this adapter. Value buffers may
alias bank data; each byte is read at its turn, preserving overwrite order.
"""

def prepare_blend_mask(mask, bank, mode):
    profile=bank.get('profile')
    if profile is None or mode not in (0,1,2):
        return []
    values=mask['mode_values'][mode]
    count=len(values)
    if count>65535:
        raise ValueError('uint16 mode byte count required')
    indices=mask['indices'];descriptors=profile['descriptors'];data=bank['data']
    visited=[]
    for i in range(count):
        offset=descriptors[indices[i]]['offset']
        if type(offset) is not int or not 0<=offset<=65535 or offset>=len(data):
            raise ValueError('descriptor byte offset outside supplied storage')
        data[offset]=values[i]
        visited.append(offset)
    return visited
