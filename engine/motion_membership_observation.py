"""Bounded passive join of a player entity to the PreBeforeSimulation motion batch.

Registry entry 24 (world+0x730) is the source list the action graph gathers into
the `Physic::PreBeforeSimulation` job's receiver storage (graph+0x4c70). That
job's callback is a two-instruction thunk that dispatches receiver table slot
0x270. Caller supplies the current player entity/world and a process-identity-
checked readv. No execution, lifetime or input-freshness proof is made.
See docs/reconstruction/MOTION_MEMBERSHIP_OBSERVATION.md.
"""
import struct
from .scheduler_observation import _address

SOURCE = 0x730            # world registry entry 24 header: pointer, count, tagged capacity
GRAPH = 0x1038            # world -> action graph
JOB = 0x4ad8              # Physic::PreBeforeSimulation job base in the graph
JOB_TABLE_RVA = 0x1ec7f38  # shared concrete range-job table (also used by AnimationUpdateTime)
CALLBACK = JOB + 0x1c0    # installed invoke field
THUNK_RVA = 0x8b9750      # mov rax,[rcx]; jmp [rax+0x270]
STORAGE = JOB + 0x198     # gathered receiver pointer, remaining-to-claim, capacity
MOTION_SLOT = 0x270
IMAGE_SPAN = 0x3600000    # receiver tables outside [base, base+span) are not followed


BATCHES = {
    'DispatchAnimEvents': (0x43d8, 0x570),  # entry 17, gather 0x8be169
    # name: (job base in the action graph, world registry entry header offset)
    'Physic::PreBeforeSimulation': (JOB, SOURCE),      # entry 24, gather 0x8be137
    'Ai::UpdateAIPreUpdate': (0x1ae0, 0x270),          # entry 5, builder 0x9119c0
    'Physic::BeforeSimulation': (0x4ca0, 0x770),       # entry 25, gather 0x8be150, thunk store 0x907e37
}
REGISTRY = 0x130          # world+0x110 registry, entries from +0x20, stride 0x40


def capture_motion_membership(readv, entity, world, image_base, guards, job=JOB, entry=SOURCE,
                              actor=None):
    """Inspect at most 256 source receivers and 1024 destination storage slots.

    `job` is the batch job base in the action graph (storage at +0x198, callback
    at +0x1c0); `entry` is its world registry entry header. Reports, per source
    receiver, whether it is exactly the supplied entity and which image
    table/dispatch method it carries. DispatchAnimEvents uses slot 0x278;
    other supported batches use 0x270. Historical motion_method_rva fields
    describe the selected dispatch_slot, not an assertion of motion semantics.
    Destination entries are compared as
    values, never dereferenced.
    """
    _address(entity, 0x68)
    _address(world, GRAPH + 8)
    _address(image_base, IMAGE_SPAN)
    names = [n for n, spec in BATCHES.items() if spec == (job, entry)]
    if not names:
        raise ValueError('unrecognised motion batch')
    storage_at, callback_at = job + 0x198, job + 0x1c0
    thunk_rva, dispatch_slot = ((0x732320, 0x278) if names[0] == 'DispatchAnimEvents'
                                else (THUNK_RVA, MOTION_SLOT))
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
            observed = read([(a, len(b)) for a, b in part])
            changed = [a for (a, expected), actual in zip(part, observed) if actual != expected]
            if changed:
                # Diagnostic addresses are session-private, not portable evidence IDs.
                raise ValueError('membership identity or storage changed at ' +
                                 ','.join(hex(a) for a in changed))

    def retain(address, size):
        _address(address, size)
        b = read([(address, size)])[0]
        guards.append((address, b))
        return b

    def q(address):
        return struct.unpack('<Q', retain(address, 8))[0]

    def image_rva(value):
        return value - image_base if image_base <= value < image_base + IMAGE_SPAN else None

    check()
    if q(entity + 0x60) != world:
        raise ValueError('entity belongs to a different world')
    graph = q(world + GRAPH)
    _address(graph, max(storage_at, callback_at) + 16)
    if q(graph) != world:
        raise ValueError('graph world backlink mismatch')
    if q(graph + job) != image_base + JOB_TABLE_RVA:
        raise ValueError('motion batch job table mismatch')
    if q(graph + callback_at) != image_base + thunk_rva:
        raise ValueError('motion batch callback mismatch')
    source, count, tagged_capacity = struct.unpack('<QiI', retain(world + entry, 16))
    storage, remaining, capacity = struct.unpack('<Qii', retain(graph + storage_at, 16))
    if not 0 <= count <= 256 or count > (tagged_capacity & 0x1fffffff):
        raise ValueError('invalid or oversized motion source')
    if not 0 <= remaining <= capacity <= 1024:
        raise ValueError('invalid or oversized motion storage')
    sources = list(struct.unpack('<' + 'Q' * count, retain(source, count * 8))) if count else []
    slots = list(struct.unpack('<' + 'Q' * capacity, retain(storage, capacity * 8))) if capacity else []

    def describe(address):
        _address(address, 24)
        head = retain(address, 24)
        table, owner = struct.unpack_from('<Q', head)[0], struct.unpack_from('<Q', head, 16)[0]
        rva = image_rva(table)
        method = image_rva(q(table + dispatch_slot)) if rva is not None else None
        return rva, method, owner

    entity_table, entity_method, _ = describe(entity)
    receivers = []
    for index, address in enumerate(sources):
        table_rva, method_rva, owner = describe(address)
        receivers.append(dict(
            source_index=index, is_entity=address == entity,
            is_actor=actor is not None and address == actor, owned_by_entity=owner == entity,
            table_rva=table_rva, motion_method_rva=method_rva,
            storage_indices=[i for i, v in enumerate(slots) if v == address],
            unclaimed_prefix_indices=[i for i, v in enumerate(slots[:remaining]) if v == address]))
    check()
    entity_rows = [r['source_index'] for r in receivers if r['is_entity']]
    actor_rows = [r['source_index'] for r in receivers if r['is_actor']]
    owned_rows = [r['source_index'] for r in receivers if r['owned_by_entity']]
    return dict(schema='motion-membership-observation-v1', batch=names[0],
                dispatch_slot=dispatch_slot, callback_rva=thunk_rva,
                registry_entry=(entry - REGISTRY) // 0x40, source_count=count,
                storage_capacity=capacity, remaining_to_claim=remaining,
                entity_table_rva=entity_table, entity_motion_method_rva=entity_method,
                receivers=receivers, entity_source_indices=entity_rows,
                actor_source_indices=actor_rows, owned_source_indices=owned_rows,
                guards_matched=True, source_membership_observed=bool(entity_rows),
                atomic_snapshot=False, callback_execution_established=False,
                input_freshness_established=False, safe_to_step_established=False,
                limits=['Storage capacity includes stale or inactive slots.',
                        'Zero remaining claims does not mean callbacks finished.',
                        'A receiver equal to the entity pointer is membership, not execution.',
                        'No entity match does not prove the player uses no other receiver object.',
                        'Repeated matching reads do not exclude intervening changes or object reuse.'])


def scan_registry(readv, entity, world, guards, entries=32, image_base=None):
    """Passively read world registry entry headers 0..entries-1 and report where
    the entity pointer appears, and which receivers are components owned by the
    entity (owner pointer at receiver+0x10, as for KinoComponent). Entries whose
    header is not a plausible pointer/count/capacity triple are reported as
    invalid, not followed. With image_base, owned receivers also report their
    table RVA and slot-0x270 method RVA."""
    if not 1 <= entries <= 64:
        raise ValueError('entries must be 1..64')
    _address(entity, 0x68)
    _address(world, REGISTRY + entries * 0x40)
    if image_base is not None:
        _address(image_base, IMAGE_SPAN)
    guards = list(guards)

    def read(plan):
        result = list(readv(plan))
        if len(result) != len(plan) or any(type(b) is not bytes or len(b) != n
                                         for b, (_, n) in zip(result, plan)):
            raise ValueError('incomplete registry read')
        return result

    def check():
        for start in range(0, len(guards), 32):
            part = guards[start:start + 32]
            if read([(a, len(b)) for a, b in part]) != [b for _, b in part]:
                raise ValueError('registry identity or storage changed')

    check()
    if read([(entity + 0x60, 8)])[0] != struct.pack('<Q', world):
        raise ValueError('entity belongs to a different world')
    headers = read([(world + REGISTRY + i * 0x40, 16) for i in range(entries)])
    rows = []
    for i, h in enumerate(headers):
        pointer, count, tagged = struct.unpack('<QiI', h)
        cap = tagged & 0x1fffffff
        row = dict(entry=i, count=count, capacity=cap, entity_indices=None,
                   owned=None, status='empty')
        if count == 0:
            pass
        elif not (0 < count <= min(cap, 256)) or not 0x10000 <= pointer < 0x800000000000:
            row['status'] = 'invalid'
        else:
            items = read([(pointer, count * 8)])[0]
            guards.extend([(world + REGISTRY + i * 0x40, h), (pointer, items)])
            values = struct.unpack('<' + 'Q' * count, items)
            row['entity_indices'] = [k for k, v in enumerate(values) if v == entity]
            row['owned'] = []
            plausible = [(k, v) for k, v in enumerate(values) if 0x10000 <= v < 0x800000000000 - 24]
            heads = read([(v, 24) for _, v in plausible]) if plausible else []
            for (k, v), head in zip(plausible, heads):
                table, owner = struct.unpack_from('<Q', head)[0], struct.unpack_from('<Q', head, 16)[0]
                if owner != entity:
                    continue
                guards.extend([(v, head[:8]), (v + 16, head[16:24])])
                item = dict(index=k, table_rva=None, motion_method_rva=None)
                if image_base is not None and image_base <= table < image_base + IMAGE_SPAN:
                    item['table_rva'] = table - image_base
                    slot = read([(table + MOTION_SLOT, 8)])[0]
                    guards.append((table + MOTION_SLOT, slot))
                    method = struct.unpack('<Q', slot)[0]
                    if image_base <= method < image_base + IMAGE_SPAN:
                        item['motion_method_rva'] = method - image_base
                row['owned'].append(item)
            row['status'] = 'read'
        rows.append(row)
    check()
    return dict(schema='registry-scan-v2', entries=rows,
                entity_entries=[r['entry'] for r in rows if r['entity_indices']],
                owned_entries=[r['entry'] for r in rows if r['owned']],
                atomic_snapshot=False, membership_is_not_execution=True,
                limits=['Ownership is the qword at receiver+0x10, proven for KinoComponent only.',
                        'Receivers of other layouts may store something else there.'])
