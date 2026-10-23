"""Read-only qualification of the inspected timing service and world membership.

Evidence: SCHEDULER_SMOOTHING_AUDIT.md, producer ordering. Layout is build-specific;
caller supplies validated module locations and a freshly acquired expected world.
Two equal sequential samples do not pin lifetimes or prove virtual execution.
"""
import struct


def observe_timing_service(read, *, singleton_address, registry_address,
                           expected_vtable, expected_dispatch, expected_world,
                           expected_manager, expected_owner):
    """Bounded to 84 reads/2048 bytes, at most 32 registered world handles.

    Addresses in the result are private provenance. No calls, writes or hooks.
    A refused or changing sample never returns partially qualified objects.
    """
    for value in (singleton_address, registry_address, expected_vtable,
                  expected_dispatch, expected_world, expected_manager, expected_owner):
        if type(value) is not int or not 0 < value < 2**64:
            raise ValueError('nonzero uint64 addresses required')
    reads = total = 0

    class Refused(Exception):
        pass

    def get(address, size):
        nonlocal reads, total
        if not 0 < address < 2**64 or address + size > 2**64:
            raise Refused('invalid_address')
        if reads >= 84 or total + size > 2048:
            raise Refused('limit')
        reads += 1
        total += size
        value = read(address, size)
        if not isinstance(value, bytes) or len(value) != size:
            raise Refused('short_read')
        return value

    def q(address):
        return struct.unpack('<Q', get(address, 8))[0]

    def sample():
        service = q(singleton_address)
        if q(service) != expected_vtable:
            raise Refused('wrong_service_type')
        if q(expected_vtable + 0x48) != expected_dispatch:
            raise Refused('dispatch_changed')
        registry = q(registry_address)
        header = get(registry + 0x72, 12)
        array = struct.unpack_from('<Q', header)[0]
        count = struct.unpack_from('<H', header, 10)[0]
        if count > 32:
            raise Refused('limit')
        handles = struct.unpack('<' + 'Q' * count, get(array, count * 8)) if count else ()
        entries = []
        for handle in handles:
            raw = get(handle, 16)
            payload = struct.unpack_from('<Q', raw)[0]
            signed_status = struct.unpack_from('<i', raw, 12)[0]
            entries.append((handle, payload, signed_status))
        # Native signed-handle resolution selects payload only for a negative
        # status word. Preserve all raw entries to detect changes between reads.
        matches = [i for i, (_, payload, status) in enumerate(entries)
                   if status < 0 and payload == expected_world]
        if len(matches) != 1:
            raise Refused('world_membership_ambiguous' if matches else 'world_absent')
        if q(expected_world + 0xff0) != expected_manager:
            raise Refused('manager_changed')
        if q(expected_manager + 0x18) != expected_owner or q(expected_owner) != expected_manager:
            raise Refused('owner_changed')
        return dict(service=service, vtable=expected_vtable, dispatch=expected_dispatch,
                    registry=registry, array=array, entries=entries, world_index=matches[0],
                    world=expected_world, manager=expected_manager, owner=expected_owner)

    try:
        first, second = sample(), sample()
        result = dict(status='qualified', binding=first) if first == second else dict(status='unstable')
    except Refused as exc:
        result = dict(status=str(exc))
    except (OSError, ValueError, struct.error):
        result = dict(status='invalid')
    return dict(result, reads=reads, bytes=total, atomic_snapshot=False,
                dispatch_execution_proved=False)
