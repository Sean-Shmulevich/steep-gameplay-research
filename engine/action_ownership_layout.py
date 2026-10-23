"""Bounded inspection of detached input-ownership table bytes.

Evidence: INPUT_UPDATE_ORDER.md, Ownership table layout and reader bank.
This describes the studied build, not portable engine addresses or live memory.
"""
import struct

TABLE_SIZE = 0xfe60
BANKS = {'previous': 8, 'current': 0x40, 'requested': 0x78, 'press_capture': 0xb0}
FAMILIES = {'fixed': (0x60, 1), 'scalar': (0x7e0, 32), 'vector': (0xefe0, 2)}


def ownership_record_offset(family, adapter_offset, channel=0):
    """Offset of one 0xe8-byte constructed record inside the detached table."""
    if family not in FAMILIES:
        raise ValueError('fixed, scalar or vector family required')
    base, channels = FAMILIES[family]
    if type(adapter_offset) is not int or not 0 <= adapter_offset < 8:
        raise ValueError('adapter offset must be 0..7')
    if type(channel) is not int or not 0 <= channel < channels:
        raise ValueError('channel outside constructed family')
    return base + 0xe8*(adapter_offset + 8*channel)


def inspect_ownership_banks(snapshot, family, adapter_offset, channel=0):
    """Return seven uint64 identities per bank, in descending priority order.

    Bank names describe observed descriptor/fixed transitions. Matching storage
    does not prove that all families share the same update policy or cadence.
    """
    if not isinstance(snapshot, bytes) or len(snapshot) != TABLE_SIZE:
        raise ValueError('0xfe60-byte table snapshot required')
    record = ownership_record_offset(family, adapter_offset, channel)
    return {name: tuple(struct.unpack_from('<Q', snapshot, record+offset+8*i)[0]
                        for i in range(6, -1, -1))
            for name, offset in BANKS.items()}
