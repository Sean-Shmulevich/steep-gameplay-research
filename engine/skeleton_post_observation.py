"""Bounded passive skeleton post-update source/storage join; no execution or lifetime proof.

Evidence: CENTRAL_IMPULSE.md, Skeleton post-update gather membership.
Caller supplies current player entity/world and process-identity-checked readv.
The returned indices reveal no raw memory or process addresses. A successful
guard recheck still permits intervening changes and allocation reuse.
"""
import struct
from .scheduler_observation import _address


def capture_skeleton_post_membership(readv, entity, world, image_base, guards):
    """Inspect at most 256 source receivers and 1024 destination storage slots.

    All observed headers, arrays and receiver identity links are rechecked.
    Stale destination pointers are compared as values, never dereferenced.
    Exceeding a bound aborts rather than reporting a truncated absence.
    """
    _address(entity, 0x68)
    _address(world, 0x1040)
    _address(image_base, 0x1f289d8)
    guards = list(guards)
    if not 1 <= len(guards) <= 30:
        raise ValueError('provide 1..30 external identity guards')
    for address, expected in guards:
        if type(expected) is not bytes or not 1 <= len(expected) <= 256:
            raise ValueError('invalid external guard')
        _address(address, len(expected))

    def read(plan):
        result = list(readv(plan))
        if len(result) != len(plan) or any(type(b) is not bytes or len(b) != n
                                         for b, (_, n) in zip(result, plan)):
            raise ValueError('incomplete membership read')
        return result

    def check():
        for start in range(0, len(guards), 32):
            part = guards[start:start + 32]
            if read([(a, len(b)) for a, b in part]) != [b for _, b in part]:
                raise ValueError('membership identity or storage changed')

    def retain(address, size):
        _address(address, size)
        b = read([(address, size)])[0]
        guards.append((address, b))
        return b

    check()
    if retain(entity + 0x60, 8) != struct.pack('<Q', world):
        raise ValueError('entity belongs to a different world')
    graph = struct.unpack('<Q', retain(world + 0x1038, 8))[0]
    _address(graph, 0x7938)
    if retain(graph, 8) != struct.pack('<Q', world):
        raise ValueError('graph world backlink mismatch')
    if retain(graph + 0x7930, 8) != struct.pack('<Q', image_base + 0xd5bff0):
        raise ValueError('skeleton post-update callback mismatch')
    source, count, tagged_capacity = struct.unpack('<QiI', retain(world + 0x4f0, 16))
    storage, remaining, capacity = struct.unpack('<Qii', retain(graph + 0x7908, 16))
    if not 0 <= count <= 256 or count > (tagged_capacity & 0x1fffffff):
        raise ValueError('invalid or oversized skeleton post source')
    if not 0 <= remaining <= capacity <= 1024:
        raise ValueError('invalid or oversized skeleton post storage')
    sources = list(struct.unpack('<' + 'Q' * count, retain(source, count * 8))) if count else []
    slots = list(struct.unpack('<' + 'Q' * capacity, retain(storage, capacity * 8))) if capacity else []
    matches = []
    for start in range(0, len(sources), 32):
        addresses = sources[start:start + 32]
        for address in addresses:
            _address(address, 24)
        headers = read([(a, 24) for a in addresses])
        for index, (address, header) in enumerate(zip(addresses, headers), start):
            guards.extend([(address, header[:8]), (address + 16, header[16:24])])
            table = struct.unpack_from('<Q', header)[0]
            owner = struct.unpack_from('<Q', header, 16)[0]
            if table == image_base + 0x1f1e598 and owner == entity:
                matches.append(dict(source_index=index,
                                    storage_indices=[i for i, value in enumerate(slots) if value == address],
                                    unclaimed_prefix_indices=[i for i, value in enumerate(slots[:remaining]) if value == address]))
    check()
    return dict(schema='skeleton-post-membership-observation-v1', source_count=count,
                storage_capacity=capacity, remaining_to_claim=remaining,
                player_skeleton_source_matches=matches, guards_matched=True,
                source_membership_observed=bool(matches), atomic_snapshot=False,
                callback_execution_established=False, safe_to_step_established=False,
                limits=['Storage capacity includes stale or inactive slots.',
                        'Zero remaining claims does not mean callbacks finished.',
                        'No source match does not establish absence from alternate update routes.',
                        'Repeated matching reads do not exclude intervening changes or object reuse.'])
