"""Bounded passive clock observation. See docs/reconstruction/CLOCK_OBSERVATION.md.

Caller owns fresh world/process identity and transport deadlines. No process API.
"""
import struct
from .animation_call_trace import decode_packet


def _scalar(data, offset):
    # Reuse the bit-preserving finite/nonfinite packet scalar decoder.
    r = decode_packet(bytes(8) + data[offset:offset + 4] + bytes(3))
    return dict(bits=r['interval_bits'], value=r['interval'], finite=r['interval_finite'])


def decode_clock(data):
    if not isinstance(data, bytes) or len(data) != 0x47:
        raise ValueError('clock requires exactly 71 bytes')
    result = {name: _scalar(data, offset) for name, offset in (
        ('interval', 0x18), ('reciprocal', 0x1c), ('previous_interval', 0x20),
        ('scale', 0x24), ('secondary_scale', 0x28))}
    result.update({name: struct.unpack_from(fmt, data, offset)[0] for name, offset, fmt in (
        ('accumulated_ticks', 0, '<Q'), ('counter', 0x2c, '<I'), ('ticks', 0x30, '<I'),
        ('toggle', 0x34, '<I'), ('hold_count', 0x38, '<i'),
        ('previous_hold_count', 0x3c, '<i'), ('pending_holds', 0x40, '<i'))})
    result['flags'] = list(data[0x44:0x47])
    return result


def capture_clocks(readv, *, image_base, world, guards):
    """Read one non-atomic sample with root/driver/link checks before and after.

    Child membership is pointer equality only. No child pointer is dereferenced.
    All addresses are current-session caller inputs, never saved defaults.
    """
    for address in (image_base, world):
        if type(address) is not int or not 0 < address < (1 << 64) - 0x4000000:
            raise ValueError('invalid base/world address')
    if not 1 <= len(guards) <= 24:
        raise ValueError('one to 24 fresh identity guards required')
    for address, expected in guards:
        if type(address) is not int or address <= 0 or not isinstance(expected, bytes) or not 1 <= len(expected) <= 256:
            raise ValueError('invalid identity guard')

    def read(ranges):
        chunks = readv(ranges)
        if len(chunks) != len(ranges) or any(not isinstance(b, bytes) or len(b) != n for b, (_, n) in zip(chunks, ranges)):
            raise ValueError('short clock read')
        return chunks

    def check(items):
        if read([(a, len(b)) for a, b in items]) != [b for _, b in items]:
            raise ValueError('clock identity or membership changed')

    check(guards)
    globals_ = [(image_base + 0x32fb438, 8), (image_base + 0x32fb600, 8),
                (image_base + 0x33060a0, 8)]
    values = read(globals_)
    root, driver, divisor = (struct.unpack('<Q', b)[0] for b in values)
    if not root or not driver or root >= (1 << 64) - 256 or driver >= (1 << 64) - 256:
        raise ValueError('missing or invalid clock root/driver')
    links = list(guards) + [(a, b) for (a, _), b in zip(globals_, values)]
    header = read([(root + 0x47, 12)])[0]
    pointer, tagged_capacity, count = struct.unpack('<QHH', header)
    capacity = tagged_capacity & 0x3fff
    if not 0 <= count <= capacity <= 512 or (count and (not pointer or pointer >= (1 << 64) - count * 8)):
        raise ValueError('clock child list exceeds observation bounds')
    links.append((root + 0x47, header))
    slots = read([(pointer, count * 8)])[0] if count else b''
    if slots: links.append((pointer, slots))
    expected_clocks = [world + o for o in (0x1048, 0x10a0, 0x10f8)]
    names = ('ordinary', 'alternate', 'third')
    children = list(struct.unpack('<' + 'Q' * count, slots)) if count else []
    check(links)
    chunks = read([(root, 0x47)] + [(a, 0x47) for a in expected_clocks] + [(driver, 0x99)])
    check(links)
    d = chunks[-1]
    return dict(atomic=False, safe_to_step_established=False,
                policy_to_world_execution_established=False,
                timer_divisor=divisor, child_count=count,
                world_child_indices={name: [i for i, a in enumerate(children) if a == target]
                                     for name, target in zip(names, expected_clocks)},
                clocks={name: decode_clock(data) for name, data in zip(('root',) + names, chunks[:4])},
                driver=dict(mode=struct.unpack_from('<I', d, 0x94)[0], rate=_scalar(d, 0x90),
                            table_index=struct.unpack_from('<i', d, 4)[0],
                            table_count=struct.unpack_from('<i', d, 8)[0],
                            stable_count=struct.unpack_from('<i', d, 0)[0],
                            table_storage=[_scalar(d, 0xc + j*4) for j in range(10)],
                            history_storage=[_scalar(d, 0x34 + j*4) for j in range(16)],
                            history_index=d[0x98]))
