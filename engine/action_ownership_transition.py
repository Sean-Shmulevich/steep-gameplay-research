"""Descriptor-record ownership update from INPUT_UPDATE_ORDER.md.

Bank names describe the observed copies, not a complete scheduler contract.
The caller supplies held/pressed booleans after native mapping and mask checks.
"""
import struct


def update_ownership_record(snapshot, *, held, pressed):
    """Return a 0xe8-byte record after its seven ownership-slot updates.

    Offsets: previous +8, current +0x40, requested +0x78, press-capture +0xb0.
    Requested storage is retained. A held current owner survives a null request.
    """
    if not isinstance(snapshot, bytes) or len(snapshot) != 0xe8:
        raise ValueError('0xe8-byte ownership record required')
    if type(held) is not bool or type(pressed) is not bool:
        raise ValueError('boolean held and pressed inputs required')
    result = bytearray(snapshot)
    for index in range(7):
        current_at = 0x40 + 8*index
        current = struct.unpack_from('<Q', result, current_at)[0]
        requested = struct.unpack_from('<Q', result, current_at+0x38)[0]
        if pressed:
            struct.pack_into('<Q', result, current_at+0x70, current)
        if not (held and current != 0 and requested == 0):
            struct.pack_into('<Q', result, current_at-0x38, current)
            struct.pack_into('<Q', result, current_at, requested)
    return bytes(result)
