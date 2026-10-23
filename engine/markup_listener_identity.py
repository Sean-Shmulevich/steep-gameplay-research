"""Recovered local descriptor comparison; no native subscription/lifetime API.

Evidence: CENTRAL_IMPULSE.md, Native listener removal and identity.
Descriptor words are function, adjustment, tagged receiver, thunk.
"""

def _descriptor(value):
    words = tuple(value)
    if len(words) != 4 or any(type(x) is not int or not 0 <= x < 2**64 for x in words):
        raise ValueError('descriptor requires four uint64 words')
    return words


def same_listener(left, right):
    """Comparison used by removal. Thunks and receiver tag bits are ignored."""
    a, b = _descriptor(left), _descriptor(right)
    ar, br = a[2] & ~3, b[2] & ~3
    if not ar:
        return not br and a[0] == b[0]
    return ar == br and a[0] == b[0] and a[1] == b[1]


def remove_first_listener(descriptors, target):
    """Local search/swap-last effect only; no destructor, map or link-count calls.

    Returns a fresh list and removed index, or None when no match exists.
    """
    target = _descriptor(target)
    result = [_descriptor(item) for item in descriptors]
    for index, item in enumerate(result):
        if same_listener(item, target):
            result[index] = result[-1]
            result.pop()
            return result, index
    return result, None
