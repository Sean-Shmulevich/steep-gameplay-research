"""Passive SkeletonComponent binding observation, with caller-supplied transport.

Profile RVAs must come from an independently verified build. Equal before/after
reads do not pin objects or establish an atomic snapshot. No process access here.
"""
import struct
from .scheduler_observation import _address


def capture_skeleton_binding(readv, entity, image_base, guards, profile, *, include_provider_bank=True):
    """Return address-free binding facts; inspect at most 256 components.

    Profile keys: entity_tables, skeleton_table, type_getter, descriptor_global.
    Set include_provider_bank=False to check component identity without retaining
    the mutable bank pointer. The separate pose reader guards its own bank read.
    All values are RVAs, entity_tables is a nonempty list. Transport must enforce
    process identity, exact reads and timeouts. Unknown derived types are omitted.
    """
    if type(include_provider_bank) is not bool:
        raise ValueError('boolean include_provider_bank required')
    _address(entity, 0x1fa)
    _address(image_base)
    guards = list(guards)
    if not 1 <= len(guards) <= 16:
        raise ValueError('provide 1..16 external identity guards')
    for address, expected in guards:
        if type(expected) is not bytes or not 1 <= len(expected) <= 256:
            raise ValueError('invalid external guard')
        _address(address, len(expected))

    def relocated(rva):
        if type(rva) is not int or not 0 <= rva <= 0xffffffff:
            raise ValueError('invalid profile RVA')
        return _address(image_base + rva)

    tables = profile['entity_tables']
    if not isinstance(tables, (list, tuple)) or not 1 <= len(tables) <= 16:
        raise ValueError('invalid entity tables')
    tables = [relocated(rva) for rva in tables]
    table, getter, descriptor_global = [relocated(profile[k]) for k in
                                       ('skeleton_table', 'type_getter', 'descriptor_global')]

    def read(plan):
        result = list(readv(plan))
        if len(result) != len(plan) or any(type(b) is not bytes or len(b) != n
                                         for b, (_, n) in zip(result, plan)):
            raise ValueError('incomplete skeleton read')
        return result

    def check():
        for start in range(0, len(guards), 32):
            part = guards[start:start + 32]
            if read([(a, len(b)) for a, b in part]) != [b for _, b in part]:
                raise ValueError('skeleton identity or storage changed')

    def retain(address, size):
        _address(address, size)
        value = read([(address, size)])[0]
        guards.append((address, value))
        return value

    def pointer(address):
        return struct.unpack('<Q', retain(address, 8))[0]

    check()
    if pointer(entity) not in tables:
        raise ValueError('entity table mismatch')
    header = retain(entity + 0x88, 12)
    array = struct.unpack_from('<Q', header)[0]
    count = struct.unpack_from('<H', header, 10)[0]
    if count > 256:
        raise ValueError('component count exceeds observation bound')
    cache = retain(entity + 0x1aa, 4)
    cached_index = struct.unpack_from('<H', cache, 2)[0]
    tag = retain(entity + 0x1f9, 1)[0]
    components = struct.unpack('<' + 'Q' * count, retain(array, count * 8)) if count else ()
    matches = []
    for start in range(0, count, 32):
        batch = components[start:start + 32]
        headers = read([(_address(a, 8), 8) for a in batch])
        for i, (address, value) in enumerate(zip(batch, headers), start):
            guards.append((address, value))
            if struct.unpack('<Q', value)[0] == table:
                matches.append(i)
    result = dict(schema='skeleton-binding-observation-v1', component_count=count,
                  exact_type_indices=matches, cached_index=cached_index,
                  cached_tag=cache[0], entity_tag=tag,
                  cache_refresh_required=cached_index == 65534 or cache[0] != tag,
                  cached_index_matches_exact_type=cached_index in matches,
                  atomic_snapshot=False, lifetime_pinned=False,
                  derived_types_classified=False, provider_bank_dereferenced=False)
    if len(matches) == 1:
        if pointer(table + 0x30) != getter:
            raise ValueError('skeleton type getter mismatch')
        displacement = descriptor_global - (getter + 7)
        if not -(1 << 31) <= displacement < (1 << 31):
            raise ValueError('type getter displacement out of range')
        if retain(getter, 8) != b'\x48\x8b\x05' + struct.pack('<i', displacement) + b'\xc3':
            raise ValueError('type getter instruction mismatch')
        descriptor = pointer(descriptor_global)
        _address(descriptor, 0x50)
        name = pointer(descriptor + 0x18)
        if retain(name, 18) != b'SkeletonComponent\0':
            raise ValueError('type descriptor name mismatch')
        bounds = struct.unpack('<HH', retain(descriptor + 0x4c, 4))
        component = components[matches[0]]
        owner = pointer(component + 0x10)
        bank = pointer(component + 0x258) if include_provider_bank else None
        result.update(type_range=list(bounds), owner_backlink_matches=owner == entity,
                      provider_bank_present=(bank != 0) if bank is not None else None,
                      provider_bank_observed=include_provider_bank, binding_status='unique_exact_type')
    else:
        result['binding_status'] = 'missing_exact_type' if not matches else 'ambiguous_exact_type'
    check()
    result['guards_matched'] = True
    return result
