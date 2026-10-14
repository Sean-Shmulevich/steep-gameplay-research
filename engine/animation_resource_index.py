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


def release_entry_eligible(current_count, flags):
    """Inner guarded release predicate; distinct from caller decrement gate."""
    count = _uint(current_count, 32)
    flags = _uint(flags, 32)
    return count == 0 and (flags & 0x05ffffff) == 0


def encode_record_index(record_word, entry_index):
    """CAS desired value: preserve high bits, replace low 19 with index+1.

    Truncation is observed behavior, not a claim that overflow indices are valid.
    """
    word = _uint(record_word, 32)
    index = _uint(entry_index, 32)
    return (word & 0xfff80000) | ((index + 1) & 0x7ffff)


def deferred_entry_decision(queued_key, current_key, flags, *, has_current_record):
    """Local consumer decision after a triple is removed from the ring.

    The queued record is deliberately absent: this consumer does not use it.
    Caller supplies observations, not a pinned/atomic native snapshot. Setting
    flags describes the successful CAS outcome, not a CAS implementation.
    """
    queued = _uint(queued_key, 64)
    current = _uint(current_key, 64)
    flags = _uint(flags, 32)
    if type(has_current_record) is not bool:
        raise ValueError('has_current_record must be bool')
    if queued != current:
        return {'action': 'skip', 'flags': flags}
    return {'action': 'dispatch_current_record' if has_current_record else 'mark_only',
            'flags': flags | 0x80000000}


def capture_resource_count(word):
    """Exchange-to-zero boundary for staged or published uint32 counts.

    Consumer uses decrement-to-zero, not a signed-positive count test. No actual
    loop is executed here; arbitrary captured counts need not fit ring occupancy.
    """
    captured = _uint(word, 32)
    return {'remaining_word': 0, 'captured': captured}


def publish_resource_count(published, captured):
    """Separate conditional atomic-add boundary; no wake operation is implied."""
    published = _uint(published, 32)
    captured = _uint(captured, 32)
    return {'published': (published + captured) & 0xffffffff,
            'atomic_add_executed': captured != 0}
