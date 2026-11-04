"""Pair link worker contact generation over the two bodies' shape entries.

Evidence: docs/reconstruction/LINK_SOLVER.md, "Pair link worker" (caller 0x18df770)
and "Pair contact generation" (this lane, RVA 0x18dd400). Leaf helpers:
lookup 0x1958d60 -> 0x1958a40, insert 0x1958b70 -> append 0x19586b0 -> entry
reserve 0x1958a90 (inline capacity 1 at link+0x68), removal 0x1959000, pair clear
0x19904e0 with 0x1958fa0 and reset 0x1986020, payload pool pop 0x18ddee0 and
return 0x18de390, both growing through 0x18def10.

Recovered local behavior: the entry double loop, its activity/mask/bounds gates,
the float32 frame composition, which pairs are cleared, the lookup / acquire /
insert / update / reset / remove / release sequence and the payload bit0 refresh.
CENTRAL_IMPULSE.md "Link keys and payload row serialization" and LINK_SOLVER.md
"Empty-pair cache recycling" describe the same key and clear rules on dict
fixtures (pose_link_record, pose_contact_cache); this module restates them over
flat memory because the caller passes raw link and owner addresses.

Supplied services (authored interface names): shape bounds (shape vtable+0x10),
handler lookup (dispatcher at provider+0x68, vtable+8), contact production
(handler vtable+0x18, capacity 500), payload update 0x198fdc0, the two terrain
wrappers 0x18e0980 / 0x18e08a0 (pose_contact_dispatch documents their bodies),
payload batch refill 0x18de060, and the allocator vtable. Native stack locals are
passed to services as bytes, not addresses: the geometry descriptor (0x93 bytes)
and the pair descriptor (0x14 bytes). Field names are structural only.
"""
import struct

from engine.pose_body_connectivity_retire import reserve_pose_pointer_vector

ENTRY_STRIDE = 0x48
CONTACT_CAPACITY = 500
PAYLOAD_REFILL_COUNT = 10
ENTRY_VECTOR_TAG = 0x2D
TERRAIN_KINDS = (6, 7)


def _f32(x):
    try:
        return struct.unpack('<f', struct.pack('<f', x))[0]
    except OverflowError:
        return float('inf') if x > 0 else float('-inf')


def _rows(mem, address):
    """Four 16-byte rows with the XYZ mask (0x3336890: lanes 0..2 kept, w = +0)."""
    out = []
    for r in range(4):
        x, y, z = struct.unpack('<3f', bytes(mem.view(address + 16 * r, 12)))
        out.append((x, y, z, 0.0))
    return out


def compose_pose_entry_frame(mem, body_frame, local_frame):
    """Body rows at body+0x40 times the entry's local rows; float32, native add order.

    rows 0..2: (A0*Lk.x + A1*Lk.y) + A2*Lk.z
    row 3:     ((A0*L3.x + A3) + A1*L3.y) + A2*L3.z
    Returns 64 bytes (the w lane is a signed zero from the masked lanes).
    """
    a = _rows(mem, body_frame)
    l = _rows(mem, local_frame)
    out = bytearray()
    for k in range(4):
        lx, ly, lz = l[k][:3]
        lane = []
        for m in range(4):
            px = _f32(a[0][m] * lx)
            py = _f32(a[1][m] * ly)
            pz = _f32(a[2][m] * lz)
            if k < 3:
                v = _f32(_f32(px + py) + pz)
            else:
                v = _f32(_f32(_f32(px + a[3][m]) + py) + pz)
            lane.append(v)
        out += struct.pack('<4f', *lane)
    return bytes(out)


def _key(first, second, detail=0):
    return (first & 0xFFFF) | ((second & 0xFFFF) << 16) | ((detail & 0xFFFFFFFF) << 32)


def lookup_pose_link_payload(mem, link, first, second, detail=0):
    """0x1958d60 -> 0x1958a40: first forward full-key match at link+0x58/+0x60, else 0."""
    entries, count = mem.q(link + 0x58), mem.d(link + 0x60)
    key = _key(first, second, detail)
    for i in range(count):
        if mem.q(entries + 16 * i) == key:
            return mem.q(entries + 16 * i + 8)
    return 0


def remove_pose_link_entry(mem, link, first, second, detail=0):
    """0x1959000: remove the last full-key match by copying the last entry over it."""
    entries, count = mem.q(link + 0x58), mem.d(link + 0x60)
    key = _key(first, second, detail)
    for i in range(count - 1, -1, -1):
        if mem.q(entries + 16 * i) == key:
            count -= 1
            mem.set_d(link + 0x60, count)
            mem.view(entries + 16 * i, 16)[:] = bytes(mem.view(entries + 16 * count, 16))
            return


def remove_pose_link_pair(mem, link, first, second):
    """0x1958fa0: last entry whose u16 fields equal the u32 arguments; detail ignored."""
    entries, count = mem.q(link + 0x58), mem.d(link + 0x60)
    for i in range(count - 1, -1, -1):
        e = entries + 16 * i
        if mem.w(e) == first and mem.w(e + 2) == second:
            payload = mem.q(e + 8)
            count -= 1
            mem.set_d(link + 0x60, count)
            mem.view(e, 16)[:] = bytes(mem.view(entries + 16 * count, 16))
            return payload
    return 0


def reset_pose_payload(mem, payload):
    """0x1986020: payload.count110 = 0."""
    mem.set_d(payload + 0x110, 0)


def _push_pointer(mem, vector, value, allocator):
    used, capacity = mem.d(vector + 8), mem.d(vector + 0xC)
    if used == capacity:
        reserve_pose_pointer_vector(mem.view(vector, 16), (capacity * 2) & 0xFFFFFFFF if capacity else 8,
                                    allocator=allocator)
    used = mem.d(vector + 8)
    mem.set_q(mem.q(vector) + used * 8, value)
    mem.set_d(vector + 8, used + 1)


def clear_pose_link_pair(mem, link, first, second, pool, *, allocator):
    """0x19904e0(link, first, second, pool): move every matching payload to pool+0x10.

    Stops at the first removed null payload (same rule as pose_contact_cache).
    """
    while True:
        payload = remove_pose_link_pair(mem, link, first, second)
        if not payload:
            return
        reset_pose_payload(mem, payload)
        _push_pointer(mem, pool + 0x10, payload, allocator)


def acquire_pose_contact_payload(mem, pool, *, allocator, refill):
    """0x18ddee0(pool): pop pool+0x10; when empty grow by 10 and refill (0x18de060)."""
    vector = pool + 0x10
    used = mem.d(vector + 8)
    if used:
        used -= 1
        mem.set_d(vector + 8, used)
        return mem.q(mem.q(vector) + used * 8)
    need = (used + PAYLOAD_REFILL_COUNT) & 0xFFFFFFFF
    capacity = mem.d(vector + 0xC)
    if need > capacity:
        reserve_pose_pointer_vector(mem.view(vector, 16), max(need, (capacity * 2) & 0xFFFFFFFF),
                                    allocator=allocator)
    elements = mem.q(vector)
    mem.set_d(vector + 8, mem.d(vector + 8) + PAYLOAD_REFILL_COUNT)
    refill(elements + used * 8, PAYLOAD_REFILL_COUNT)
    mem.set_d(vector + 8, mem.d(vector + 8) - 1)
    return mem.q(mem.q(vector) + mem.d(vector + 8) * 8)


def release_pose_contact_payload(mem, pool, payload, *, allocator):
    """0x18de390(pool, payload): reset count110, then push to pool+0x10 (8 or 2*cap)."""
    reset_pose_payload(mem, payload)
    _push_pointer(mem, pool + 0x10, payload, allocator)


def reserve_pose_link_entries(mem, vector, capacity, *, allocator):
    """0x1958a90: 16-byte entry vector with inline one-entry storage at vector+0x10.

    vector: pointer q@0, count u32@8, capacity u32@0xC (link+0x58 in a link).
    """
    capacity &= 0xFFFFFFFF
    if capacity == mem.d(vector + 0xC):
        return
    inline = vector + 0x10
    pointer = mem.q(vector)
    size = (capacity << 4) & 0xFFFFFFFF
    if capacity > 1:
        if pointer == inline:
            new = allocator.allocate(size, 0x10, ENTRY_VECTOR_TAG)
            n = mem.d(vector + 8) * 16
            if n:
                mem.view(new, n)[:] = bytes(mem.view(inline, n))
            mem.set_q(vector, new)
        else:
            mem.set_q(vector, allocator.reallocate(pointer, size, 0x10, ENTRY_VECTOR_TAG))
        mem.set_d(vector + 0xC, capacity)
    else:
        if pointer != inline:
            if capacity:
                mem.view(inline, 16)[:] = bytes(mem.view(pointer, 16))
            allocator.release(pointer)
            mem.set_q(vector, inline)
        mem.set_d(vector + 0xC, 1)
    if mem.d(vector + 8) > capacity:
        mem.set_d(vector + 8, capacity)


def insert_pose_link_payload(mem, link, first, second, detail, payload, *, allocator):
    """0x1958b70: payload.owner0 = link, then append (0x19586b0) at link+0x58."""
    mem.set_q(payload, link)
    vector = link + 0x58
    used, capacity = mem.d(vector + 8), mem.d(vector + 0xC)
    if used == capacity:
        reserve_pose_link_entries(mem, vector, (capacity * 2) & 0xFFFFFFFF, allocator=allocator)
    used = mem.d(vector + 8)
    entry = mem.q(vector) + used * 16
    mem.set_d(vector + 8, used + 1)
    mem.put('<H', entry, first & 0xFFFF)
    mem.put('<H', entry + 2, second & 0xFFFF)
    mem.set_q(entry + 8, payload)
    mem.set_d(entry + 4, detail)


def _active(flags):
    return (flags >> 1) & flags & 4 != 0          # bits 2 and 3


def _contact_bit(flags):
    return (flags >> 2) & flags & 4 != 0          # bits 2 and 4


def _kind(mem, shape):
    return mem.w(shape + 0x28) & 0x7FFF


def _floats(raw):
    return struct.unpack('<6f', raw)


def _ge(a, b):
    """comiss a, b; jb rejects: True only for ordered a >= b."""
    return a >= b


def generate_pose_pair_contacts(mem, owner, first, second, link, same, services):
    """0x18dd400(owner, first, second, link, same).

    services: shape_bounds(shape, frame64) -> 24 bytes (min xyz, max xyz);
    lookup_handler(dispatcher, shape_a, shape_b) -> handler;
    produce_contacts(handler, descriptor, scratch, 500) -> count;
    update_payload(payload, pair, scratch, count); terrain_narrow / terrain_wide
    (owner, descriptor, pair, link) for 0x18e0980 / 0x18e08a0;
    refill_payloads(dest, 10); allocator (allocate / reallocate / release).
    """
    pool = owner + 0x28
    count_a, count_b = mem.w(first + 0xC0), mem.w(second + 0xC0)
    multi = count_a > 1 or count_b > 1
    alloc = services.allocator

    def clear(i, j):
        clear_pose_link_pair(mem, link, i, j, pool, allocator=alloc)

    for i in range(count_a):
        entries_a = mem.q(first + 0xB8)
        ea = entries_a + i * ENTRY_STRIDE
        shape_a = mem.q(ea + 0x10)
        if not shape_a or not _active(mem.b(ea + 0x44)):
            continue
        tail = bytes((1, 1 if (mem.b(first + 0xAA) & 0x40 or mem.b(second + 0xAA) & 0x40) else 0, 1))
        frame_a = compose_pose_entry_frame(mem, first + 0x40, mem.q(ea + 0x18))
        kind_a = _kind(mem, shape_a)
        a_is6 = kind_a == 6
        a_terrain = kind_a in TERRAIN_KINDS
        masks_a = mem.q(shape_a + 0x20) + 0x48
        if multi:
            box_a = _floats(services.shape_bounds(shape_a, frame_a))
            bounds = mem.q(second + 0x30)
            limit = struct.unpack('<6f', bytes(mem.view(bounds + 4, 24)))
            if not (all(_ge(box_a[3 + k], limit[k]) for k in range(3))
                    and not any(box_a[k] > limit[3 + k] for k in range(3))):
                for j in range(count_b):
                    clear(i, j)
                continue
        for j in range(count_b):
            entries_b = mem.q(second + 0xB8)
            eb = entries_b + j * ENTRY_STRIDE
            shape_b = mem.q(eb + 0x10)
            if not shape_b or not _active(mem.b(eb + 0x44)):
                continue
            kind_b = _kind(mem, shape_b)
            b_is6 = kind_b == 6
            b_terrain = kind_b in TERRAIN_KINDS
            data_b = mem.q(shape_b + 0x20)
            wide = (mem.q(eb + 0x30) & mem.q(ea + 0x28)) | (mem.q(ea + 0x30) & mem.q(eb + 0x28))
            narrow = (mem.d(eb + 0x38) & mem.d(ea + 0x3C)) | (mem.d(eb + 0x3C) & mem.d(ea + 0x38))
            if not same:
                hit = wide != 0
            elif mem.b(mem.q(first + 0x30) + 0x52) & 0x10:
                hit = narrow != 0
            else:
                hit = wide != 0 and narrow != 0
            if not hit or not ((mem.q(data_b + 0x50) & mem.q(masks_a))
                               | (mem.q(masks_a + 8) & mem.q(data_b + 0x48))):
                clear(i, j)
                continue
            if a_terrain and b_terrain:
                continue
            frame_b = compose_pose_entry_frame(mem, second + 0x40, mem.q(eb + 0x18))
            if count_b > 1:
                box_b = _floats(services.shape_bounds(shape_b, frame_b))
                if not (all(_ge(box_a[3 + k], box_b[k]) for k in range(3))
                        and all(_ge(box_b[3 + k], box_a[k]) for k in range(3))):
                    clear(i, j)
                    continue
            descriptor = frame_a + frame_b + struct.pack('<QQ', shape_a, shape_b) + tail
            pair = struct.pack('<QQHH', first, second, i, j)
            if a_terrain or b_terrain:
                if b_is6 or a_is6:
                    services.terrain_narrow(owner, descriptor, pair, link)
                else:
                    services.terrain_wide(owner, descriptor, pair, link)
                continue
            payload = lookup_pose_link_payload(mem, link, i, j, 0)
            handler = services.lookup_handler(mem.q(mem.q(owner) + 0x68), shape_a, shape_b)
            scratch = mem.q(owner + 0x58)
            count = services.produce_contacts(handler, descriptor, scratch, CONTACT_CAPACITY)
            if count:
                if not payload:
                    payload = acquire_pose_contact_payload(mem, pool, allocator=alloc,
                                                           refill=services.refill_payloads)
                    insert_pose_link_payload(mem, link, i, j, 0, payload, allocator=alloc)
                services.update_payload(payload, pair, scratch, count)
            elif payload:
                reset_pose_payload(mem, payload)
            if not payload:
                continue
            if mem.d(payload + 0x110) == 0:
                remove_pose_link_entry(mem, link, i, j, 0)
                release_pose_contact_payload(mem, pool, payload, allocator=alloc)
            else:
                bit = (_contact_bit(mem.b(mem.q(first + 0xB8) + i * ENTRY_STRIDE + 0x44))
                       and _contact_bit(mem.b(mem.q(second + 0xB8) + j * ENTRY_STRIDE + 0x44)))
                mem.set_b(payload + 0x114, (mem.b(payload + 0x114) & 0xFE) | int(bit))
