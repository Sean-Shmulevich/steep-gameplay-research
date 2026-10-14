"""Recovered resource-entry address arithmetic; no memory access or loading.

Evidence: docs/reconstruction/research/animation.md, Shared entry lookup.
These helpers return offsets and branch decisions only. They do not validate
native allocation, lifetime, pointer identity, or resource readiness.
"""


def _uint(value, bits):
    if type(value) is not int or not 0 <= value < (1 << bits):
        raise ValueError(f'expected uint{bits}')
    return value


def decode_record_index(record_word):
    """Decode the low-19-bit one-based index; zero means no cached index.

    Block descriptors have stride 16; entries within each block have stride 24.
    The native routine does not perform array-bounds validation here.
    """
    encoded = _uint(record_word, 32) & 0x7ffff
    if encoded == 0:
        return None
    index = encoded - 1
    block, slot = index >> 14, index & 0x3fff
    return {'index': index, 'block': block, 'slot': slot,
            'descriptor_offset': block * 16, 'entry_offset': slot * 24}


def publish_in_key_map(resource_key):
    """New entries skip map publication for inclusive range F0000000..F7FFFFFF.

    Match the unsigned 64-bit add/compare, including wraparound. This says
    nothing about what that key range denotes.
    """
    key = _uint(resource_key, 64)
    shifted = (key + 0xffffffff10000000) & 0xffffffffffffffff
    return shifted > 0x7ffffff


def needs_release_call(previous_count, flags):
    """Caller gate following atomic decrement, not a destruction guarantee."""
    count = _uint(previous_count, 32)
    flags = _uint(flags, 32)
    return count == 1 and (flags & 0xffffff) == 0
