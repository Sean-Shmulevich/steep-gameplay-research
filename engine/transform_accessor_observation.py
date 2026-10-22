"""Passive accessor linkage and synchronization metadata, without matrix payloads.

Evidence: CENTRAL_IMPULSE.md, Passive accessor preflight observations.
Requires a process-identity-checked readv and fresh external entity guards.
Rechecks do not pin lifetime, prevent address reuse, or authorize native calls.
"""
import struct
from .scheduler_observation import _address


def capture_transform_accessor(readv, entity, guards):
    _address(entity, 0x20)
    guards = list(guards)
    if not 1 <= len(guards) <= 30:
        raise ValueError('provide 1..30 identity guards')
    for address, expected in guards:
        if type(expected) is not bytes or not 1 <= len(expected) <= 256:
            raise ValueError('invalid identity guard')
        _address(address, len(expected))

    def read(plan):
        result = list(readv(plan))
        if len(result) != len(plan) or any(type(b) is not bytes or len(b) != n
                                         for b, (_, n) in zip(result, plan)):
            raise ValueError('incomplete accessor read')
        return result

    def check():
        for start in range(0, len(guards), 32):
            group = guards[start:start+32]
            if read([(a, len(b)) for a, b in group]) != [b for _, b in group]:
                raise ValueError('accessor identity or state changed')

    def observe(address, length):
        _address(address, length)
        data = read([(address, length)])[0]
        guards.append((address, data))
        return data

    check()
    pointer = struct.unpack('<Q', observe(entity+0x18, 8))[0]
    state = None
    if pointer:
        _address(pointer, 0x99)
        backlink = struct.unpack('<Q', observe(pointer+0x40, 8))[0]
        if backlink != entity:
            raise ValueError('accessor entity backlink mismatch')
        word, owner, depth, bypass = struct.unpack('<IIIB', observe(pointer+0x8c, 13))
        state = dict(reader_word=word, reader_units=word & 0xfffff,
                     writer_units=(word & 0x7ff00000) >> 20,
                     high_bit=bool(word & 0x80000000),
                     owner_thread=None if owner == 0xffffffff else owner,
                     depth=depth, owner_bypass_enabled=bool(bypass),
                     owner_bypass_raw=bypass)
    check()
    return dict(schema='transform-accessor-observation-v1',
                source='indirect' if pointer else 'inline',
                accessor_present=bool(pointer), state=state,
                guards_matched=True, atomic_snapshot=False,
                lifetime_retained=False, safe_native_call_established=False,
                freshness_established=False, matrix_read=False)
