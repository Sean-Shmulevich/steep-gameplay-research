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
    if type(count) is not int or not 0 <= count <= 255:
        raise ValueError('expected uint8 key count')
    if type(hint) is not int or not 0 <= hint <= 0xffffffff:
        raise ValueError('expected uint32 time hint')
    if type(cursor) is not int or not 0 <= cursor <= 0xffffffff:
        raise ValueError('expected uint32 cursor')
    ticks = tuple(stored_ticks)
    if len(ticks) != max(0, count-1):
        raise ValueError('stored times must exclude the implicit first key')
    if any(type(t) is not int or not 0 <= t <= 255 for t in ticks):
        raise ValueError('expected uint8 stored times')
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
