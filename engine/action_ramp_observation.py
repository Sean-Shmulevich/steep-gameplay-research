"""Bounded read-only ramp configuration receipt, not an atomic snapshot.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Bounded ramp settings reader.
Caller establishes current build, process identity and fresh chain provenance.
No calls into the game, writes, dynamic timer capture or saved heap addresses.
"""
import math
import struct


def observe_ramp_settings(read, processor, expected_table, expected_callback, manager_slot):
    """Two matching receipts, <=64 keys, <=32 reads and <=4608 bytes.

    Runtime addresses in the result are private-session provenance. A successful
    receipt proves neither execution nor thread-local configuration availability.
    """
    for value in (processor, expected_table, expected_callback, manager_slot):
        if type(value) is not int or not 0 < value < 1 << 64:
            raise ValueError('nonzero uint64 identities required')
    reads = 0
    total = 0
    class Refused(Exception):pass
    def get(address, size):
        nonlocal reads, total
        if not 0 < address < 1 << 64 or address + size > 1 << 64:
            raise Refused('invalid')
        if reads + 1 > 32 or total + size > 4608:
            raise Refused('limit')
        reads += 1
        total += size
        data = read(address, size)
        if not isinstance(data, bytes) or len(data) != size:
            raise Refused('invalid')
        return data
    def q(address):return struct.unpack('<Q', get(address, 8))[0]
    def sample():
        table = q(processor)
        if table != expected_table or q(table + 0x28) != expected_callback:
            raise Refused('unsupported')
        manager = q(manager_slot)
        if not manager:raise Refused('invalid')
        gate = bool(get(manager + 0x91, 1)[0])
        handle = q(processor + 0xd0)
        if not handle:raise Refused('invalid')
        obj = q(handle)
        active = bool(get(handle + 15, 1)[0] & 0x80)
        result = {'processor':processor, 'table':table, 'callback':expected_callback,
                  'manager':manager, 'global_gate':gate, 'handle':handle,
                  'configuration_pointer':obj, 'configuration_active':active}
        if not active or not obj:
            result['availability'] = 'unresolved'
            return result
        raw = get(obj + 0x28, 8)
        duration, mode = struct.unpack('<fI', raw)
        if not math.isfinite(duration) or duration <= 0:
            raise Refused('unsupported')
        curve = q(processor + 0xe0)
        if not curve:raise Refused('invalid')
        count = struct.unpack('<H', get(processor + 0xf6, 2))[0]
        header = get(curve + 0x10, 30)
        keys_ptr = struct.unpack_from('<Q', header)[0]
        key_count = struct.unpack_from('<H', header, 10)[0]
        if key_count > 64:raise Refused('limit')
        bounds = struct.unpack_from('<4f', header, 12)
        input_bounds = bounds[:2] if header[28] else None
        output_bounds = bounds[2:] if header[29] else None
        for selected in (input_bounds, output_bounds):
            if selected and not all(map(math.isfinite, selected)):
                raise Refused('unsupported')
        if key_count and not keys_ptr:raise Refused('invalid')
        payload = get(keys_ptr, key_count * 32) if key_count else b''
        keys = []
        previous = -math.inf
        for index in range(key_count):
            values = struct.unpack_from('<6fI', payload, index * 32)
            if not all(map(math.isfinite, values[:6])) or values[0] < previous:
                raise Refused('unsupported')
            previous = values[0]
            # Hex preserves signed zero for receipt equality and exact replay.
            keys.append({'x':values[0], 'y':values[1], 'incoming':values[2:4],
                         'outgoing':values[4:6], 'mode':values[6],
                         'semantic_hex':payload[index*32:index*32+28].hex()})
        result.update(availability='active_handle', duration=duration, axis_mode=mode,
                      parameter_hex=raw.hex(), axis_count=count, curve=curve,
                      keys_pointer=keys_ptr, keys=keys, input_bounds=input_bounds,
                      output_bounds=output_bounds,
                      bounds_hex=(header[12:20].hex() if input_bounds else None,
                                  header[20:28].hex() if output_bounds else None))
        return result
    try:
        first, second = sample(), sample()
        result = {'status':'observed', 'settings':first} if first == second else {'status':'unstable'}
    except Refused as exc:result = {'status':str(exc)}
    except (OSError, ValueError, struct.error):result = {'status':'invalid'}
    result.update(reads=reads, bytes=total)
    return result
