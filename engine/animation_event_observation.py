"""Bounded read-only Kino event queue inspection for the documented image.

Evidence: ANIMATION_COMPONENT_DISPATCH.md, Queued event drain and Named event
 types. This is an observation adapter, not a handler hook or a lifetime pin.
The transport must check process identity and impose timeouts. No writes occur.
"""
import struct
from .scheduler_observation import _address

_TYPES = {0x1eecd58: 'AudioEventSeed', 0x1eece18: 'SoundSetEventSeed'}


def capture_event_queue(readv, component, owner, image_base, image_size, guards):
    """Read at most 64 queued rows, with header/identity/content rechecks.

    Caller supplies freshly acquired component/owner identities and 1..30
    external guards. Context pointers are represented by capture-local aliases;
    their payloads are never dereferenced. Equal repeated reads are not atomic.
    """
    _address(component, 0x220)
    _address(owner)
    if type(image_size) is not int or not 0x1f28a00 <= image_size <= 0x40000000:
        raise ValueError('invalid image size')
    _address(image_base, image_size)
    retained = list(guards)
    if not 1 <= len(retained) <= 30:
        raise ValueError('provide 1..30 external identity guards')
    for address, expected in retained:
        if type(expected) is not bytes or not 1 <= len(expected) <= 256:
            raise ValueError('invalid external guard')
        _address(address, len(expected))

    def read(plan):
        result = []
        for start in range(0, len(plan), 32):
            batch = plan[start:start+32]
            for address, size in batch:
                _address(address, size)
            blocks = list(readv(batch))
            if len(blocks) != len(batch) or any(type(b) is not bytes or len(b) != n
                                               for b, (_, n) in zip(blocks, batch)):
                raise ValueError('incomplete event queue read')
            result.extend(blocks)
        return result

    def keep(plan):
        blocks = read(plan)
        retained.extend((a, b) for (a, _), b in zip(plan, blocks))
        return blocks

    def check():
        if read([(a, len(b)) for a, b in retained]) != [b for _, b in retained]:
            raise ValueError('event queue identity or content changed')

    check()
    table, owner_bytes = keep([(component, 8), (component+16, 8)])
    if struct.unpack('<Q', table)[0] != image_base+0x1f289d0:
        raise ValueError('not the expected Kino component table')
    if struct.unpack('<Q', owner_bytes)[0] != owner:
        raise ValueError('component owner mismatch')
    queue = component+0xf0
    headers = keep([(queue+offset, 12) for offset in (0, 0x90, 0x120)])
    arrays, counts = [], []
    for h in headers:
        address, tagged_capacity, count = struct.unpack('<QHH', h)
        if count > 64 or count > (tagged_capacity & 0x3fff):
            raise ValueError('invalid or oversized event queue')
        arrays.append(address)
        counts.append(count)
    if len(set(counts)) != 1:
        raise ValueError('parallel event queue counts disagree')
    count = counts[0]
    rows = []
    aliases = {}
    def context(pointer, status):
        active = bool(status & 0x80000000)
        value = pointer if active else 0
        alias = None
        if value:
            alias = aliases.setdefault(value, 'context-' + str(len(aliases)+1))
        return dict(active=active, nonnull=bool(value), alias=alias,
                    matches_owner=bool(value and value == owner),
                    matches_component=bool(value and value == component))

    if count:
        vectors = [struct.unpack('<'+'Q'*count, b) for b in
                   keep([(a, count*8) for a in arrays])]
        entries = list(zip(*vectors))
        active_entries = [(i, event, first, second) for i, (event, first, second)
                          in enumerate(entries) if event]
        tables = keep([(event, 8) for _, event, _, _ in active_entries])
        event_tables = {i: struct.unpack('<Q', raw)[0]
                        for (i, _, _, _), raw in zip(active_entries, tables)}
        def inside_table(address):
            return image_base <= address and address+0x58 <= image_base+image_size
        unique_tables = sorted({t for t in event_tables.values() if inside_table(t)})
        handlers = {t: struct.unpack('<Q', raw)[0] for t, raw in zip(
            unique_tables, keep([(t+0x50, 8) for t in unique_tables]))}
        handle_plan = []
        for _, _, first, second in active_entries:
            handle_plan.extend([(first, 8), (first+12, 4), (second, 8), (second+12, 4)])
        # Reference counts are not used by resolution and change independently.
        handle_blocks = keep(handle_plan)
        handle_values = {entry[0]: handle_blocks[n*4:n*4+4]
                         for n, entry in enumerate(active_entries)}
        for index, (event, first, second) in enumerate(entries):
            row = dict(index=index, event_present=bool(event))
            if event:
                event_table = event_tables[index]
                in_image = inside_table(event_table)
                row['table_in_image'] = in_image
                row['table_rva'] = event_table-image_base if in_image else None
                row['type_name'] = _TYPES.get(row['table_rva'], 'unknown')
                handler = handlers.get(event_table, 0)
                row['handler_in_image'] = image_base <= handler < image_base+image_size
                row['handler_rva'] = handler-image_base if row['handler_in_image'] else None
                values = handle_values[index]
                row['first'] = context(struct.unpack('<Q', values[0])[0], struct.unpack('<I', values[1])[0])
                row['second'] = context(struct.unpack('<Q', values[2])[0], struct.unpack('<I', values[3])[0])
            rows.append(row)
    check()
    return dict(schema='animation-event-queue-observation-v1', count=count, rows=rows,
                guards_matched=True, atomic_snapshot=False,
                callback_execution_established=False,
                limits=['An empty queue can mean not yet produced or already drained.',
                        'Matching reads do not exclude intervening changes or object reuse.',
                        'Context aliases are valid only within this capture.',
                        'Known table names do not establish event effects or local-player identity.'])
