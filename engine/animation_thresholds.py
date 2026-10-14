"""Recovered GetUpdateThresholds payload construction over resolved components.

Component resolution, live ownership and source-table population stay external.
Only the last payload byte is joined to animation deferral threshold here.
"""
import struct


def _uint(value, bits):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(f'expected uint{bits}')
    return value


def update_threshold_packet(*, first_component=None, second_component=None,
                            table_words=()):
    """Return the seven bytes written by the original callback.

    first_component supplies selector_word:uint16. second_component supplies
    kind:uint32 and threshold:uint8. None models a failed component lookup.
    The uint32 table payload remains raw bits; its semantic type is unproved.
    """
    packet = bytearray(struct.pack('<IBBB', 0, 1, 2, 0))
    if first_component is None or second_component is None:
        return bytes(packet)
    kind = _uint(second_component['kind'], 32)
    threshold = _uint(second_component['threshold'], 8)
    if kind == 40:
        packet[4:6] = bytes((3, 10))
    else:
        index = (_uint(first_component['selector_word'], 16) >> 3) & 7
        if index >= len(table_words):
            raise ValueError('threshold table index out of bounds')
        struct.pack_into('<I', packet, 0, _uint(table_words[index], 32))
    packet[6] = threshold
    return bytes(packet)


def deferral_threshold(packet):
    """Read the byte joined to the outer animation update's counter comparison."""
    if not isinstance(packet, bytes) or len(packet) != 7:
        raise ValueError('expected seven-byte threshold packet')
    return packet[6]
