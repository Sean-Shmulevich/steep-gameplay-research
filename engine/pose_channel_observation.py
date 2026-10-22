"""Bounded pose-channel reader using recovered layout and supplied record bounds.

The caller verifies component identity, build and process identity. Record bounds
can come from decoded metadata or an independently verified caller value.
No process operations occur here. Rechecks are not atomicity or lifetime proof.
"""
import math
import struct
from .scheduler_observation import _address
from reference.ground_response_pose import pose_channel_index, provider_pose_transform, pose_bank_layout


def capture_pose_channels(readv, component, keys, record_count, guards):
    """Read up to 16 requested channels, returning local and converted transforms.

    Set record_count=None to decode the bank metadata bound; an integer is an
    independently verified caller bound. Metadata fit is checked before reads.
    At most 4096 lookup entries are inspected; oversized tables are rejected.
    Missing keys are reported without dereferencing their 0xffff sentinel.
    """
    _address(component, 0x260)
    keys = list(keys)
    if not 1 <= len(keys) <= 16 or any(type(k) is not int or not 0 <= k < 2**32 for k in keys):
        raise ValueError('provide 1..16 uint32 channel keys')
    if record_count is not None and (type(record_count) is not int or not 0 <= record_count <= 65535):
        raise ValueError('caller-verified record count required')
    guards = list(guards)
    if not 1 <= len(guards) <= 16:
        raise ValueError('provide 1..16 identity and record-bound guards')
    for address, value in guards:
        if type(value) is not bytes or not 1 <= len(value) <= 256:
            raise ValueError('invalid external guard')
        _address(address, len(value))

    def read(plan):
        result = list(readv(plan))
        if len(result) != len(plan) or any(type(b) is not bytes or len(b) != n
                                         for b, (_, n) in zip(result, plan)):
            raise ValueError('incomplete pose-channel read')
        return result

    def check():
        for start in range(0, len(guards), 32):
            part = guards[start:start + 32]
            if read([(a, len(b)) for a, b in part]) != [b for _, b in part]:
                raise ValueError('pose-channel identity or data changed')

    def retain(address, size):
        _address(address, size)
        chunks = []
        for offset in range(0, size, 4096):
            n = min(4096, size - offset)
            b = read([(address + offset, n)])[0]
            guards.append((address + offset, b))
            chunks.append(b)
        return b''.join(chunks)

    def pointer(address):
        return struct.unpack('<Q', retain(address, 8))[0]

    check()
    table = pointer(component + 0x240)
    entries = None
    if table:
        _address(table, 0x44)
        header = retain(table + 0x38, 12)
        entry_base = struct.unpack_from('<Q', header)[0]
        count = struct.unpack_from('<H', header, 10)[0]
        if count > 4096:
            raise ValueError('channel table exceeds observation bound')
        entries = list(struct.iter_unpack('<II', retain(entry_base, count * 8))) if count else []
    indices = [pose_channel_index(entries, key) for key in keys]
    for index in indices:
        if record_count is not None and index != 65535 and index >= record_count:
            raise ValueError('channel index exceeds caller-verified record count')
    count_source = 'caller_verified' if record_count is not None else 'metadata_not_read'
    layout = None
    rows = [dict(key=key, index=index, found=index != 65535) for key, index in zip(keys, indices)]
    if any(row['found'] for row in rows):
        bank = pointer(component + 0x258)
        _address(bank, 0x1a0)
        flags = struct.unpack('<I', retain(bank + 0x8c, 4))[0]
        if record_count is None:
            metadata = pointer(bank + 0x190)
            _address(metadata, 0x5c)
            primary, alternate = struct.unpack('<HH', retain(metadata + 0x14, 4))
            record_count = struct.unpack('<H', retain(metadata + 0x5a, 2))[0]
            layout = pose_bank_layout(flags, primary, alternate, record_count)
            if not layout['transforms_fit_allocation']:
                raise ValueError('metadata transform range exceeds selected allocation size')
            if any(i != 65535 and i >= record_count for i in indices):
                raise ValueError('channel index exceeds metadata record count')
            count_source = 'native_metadata'
        parent = struct.unpack('<8f', retain(bank, 32))
        records = pointer(bank + 0x198)
        _address(records, record_count * 32)
        decoded = {}
        for index in dict.fromkeys(i for i in indices if i != 65535):
            lanes = struct.unpack('<8f', retain(records + index * 32, 32))
            if not all(math.isfinite(x) for x in parent + lanes):
                raise ValueError('nonfinite pose transform')
            args = dict(position=list(lanes[:4]), rotation=list(lanes[4:]),
                        parent_position=list(parent[:4]), parent_rotation=list(parent[4:]),
                        direct=bool(flags & (1 << 26)))
            converted = provider_pose_transform(**args)
            if not all(math.isfinite(x) for value in converted.values() for x in value):
                raise ValueError('nonfinite converted pose')
            decoded[index] = dict(inputs=args, converted=converted)
        for row in rows:
            if row['found']:
                row.update(decoded[row['index']])
    check()
    return dict(schema='pose-channel-observation-v1', channels=rows,
                guards_matched=True, atomic_snapshot=False, lifetime_pinned=False,
                record_count_source=count_source, record_count=record_count, bank_layout=layout,
                component_identity_source='caller_verified',
                coordinate_space_semantics='native_provider_conversion_only',
                clip_identity_established=False)


def capture_pose_interval(readv, component, keys, record_count, guards):
    """Bracket a pose read with the recovered bank-selection state.

    See CENTRAL_IMPULSE.md, Epoch-gated skeleton bank rotation and publication.
    This additional rejection guard is an observer policy, not a native fence.
    Equal endpoints cannot detect ABA changes or writes within the same epoch.
    No raw bank addresses are returned. Configured slots may alias.
    """
    _address(component, 0xc5c)
    plan = [(component + 0x258, 32), (component + 0xc58, 4)]

    def boundary():
        result = list(readv(plan))
        if len(result) != 2 or any(type(b) is not bytes or len(b) != n
                                   for b, (_, n) in zip(result, plan)):
            raise ValueError('incomplete pose boundary read')
        return result

    before = boundary()
    result = capture_pose_channels(readv, component, keys, record_count, guards)
    after = boundary()
    if before != after:
        raise ValueError('pose bank selection or epoch changed during observation')
    current, previous, slot_a, slot_b = struct.unpack('<4Q', before[0])
    slots = (slot_a, slot_b)
    result['selection_boundary'] = dict(
        stored_epoch=struct.unpack('<I', before[1])[0],
        current_slot_matches=[i for i, bank in enumerate(slots) if bank and bank == current],
        previous_slot_matches=[i for i, bank in enumerate(slots) if bank and bank == previous],
        configured_slots_alias=bool(slot_a and slot_a == slot_b),
        endpoints_matched=True, animation_completion_established=False,
        aba_excluded=False)
    return result
