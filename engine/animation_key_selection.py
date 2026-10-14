"""Recovered byte-time key selection, independent of channel payload decoding.

Evidence: docs/reconstruction/ANIMATION_KEY_SELECTION.md. Ticks and hints are
integers; this helper does not infer seconds or choose a keyframe payload.
"""


def select_byte_key(count, stored_ticks, hint, cursor=0xffffffff):
    """Return source key, packed tick pair and search path for caller-owned data.

    First key time is implicit zero. Packed result has current tick low16 and
    next tick high16, or zero high16 after the last key. Validation and path
    labels are reconstruction API behavior; selection follows the native helper.
    """
    return _select_list_key(count,stored_ticks,hint,cursor,255)


def select_wide_key(count,stored_ticks,hint,cursor=0xffffffff):
    """Recovered uint16 count/time variant at 0x140d581f0; same search policy."""
    return _select_list_key(count,stored_ticks,hint,cursor,65535)


def _select_list_key(count,stored_ticks,hint,cursor,limit):
    if type(count) is not int or not 0 <= count <= limit:
        raise ValueError('key count outside supported range')
    if type(hint) is not int or not 0 <= hint <= 0xffffffff:
        raise ValueError('expected uint32 time hint')
    if type(cursor) is not int or not 0 <= cursor <= 0xffffffff:
        raise ValueError('expected uint32 cursor')
    ticks = tuple(stored_ticks)
    if len(ticks) != max(0, count-1):
        raise ValueError('stored times must exclude the implicit first key')
    if any(type(t) is not int or not 0 <= t <= limit for t in ticks):
        raise ValueError('stored time outside supported range')
    if any(a > b for a, b in zip(ticks, ticks[1:])):
        raise ValueError('expected nondecreasing stored times')
    if count < 2:
        return {'cursor': 0, 'packed_ticks': 0, 'path': 'short'}
    times = (0,) + ticks
    if cursor < count and hint >= times[cursor]:
        after = cursor + 1
        while after < count and times[after] <= hint:
            after += 1
        path = 'forward'
    else:
        first, remaining = 1, count-1
        while remaining:
            half = remaining // 2
            middle = first + half
            if hint >= times[middle]:
                first = middle + 1
                remaining -= half + 1
            else:
                remaining = half
        after, path = first, 'binary'
    selected = after - 1
    packed = times[selected]
    if after < count:
        packed |= times[after] << 16
    return {'cursor': selected, 'packed_ticks': packed, 'path': path}


def select_mask_key(mode, mask_bytes, hint):
    """Recovered packed-mask selector; no prior cursor is read.

    mode low6 is mask byte length, high2 is tick shift. Native searches backward
    without a lower bound, so this API requires bit zero and nonzero mask size.
    Evidence: ANIMATION_MASK_KEY_SELECTION.md.
    """
    if type(mode) is not int or not 0<=mode<=255:
        raise ValueError('expected uint8 mask mode')
    if type(hint) is not int or not 0<=hint<=0xffffffff:
        raise ValueError('expected uint32 time hint')
    data=bytes(mask_bytes);size=mode&63;shift=mode>>6
    if size==0 or len(data)!=size or not data[0]&1:
        raise ValueError('expected nonempty mask with initial key bit')
    mask=int.from_bytes(data,'little');limit=size*8
    position=min(hint>>shift,limit-1)
    previous=position
    while not (mask>>previous)&1:previous-=1
    after=position+1
    while after<limit and not (mask>>after)&1:after+=1
    packed=previous
    if after<limit:packed|=after<<16
    return {'cursor':(mask&((1<<previous)-1)).bit_count(),
            'packed_ticks':(packed<<shift)&0xffffffff,'path':'mask_scan'}
