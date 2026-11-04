"""Per-worker pair job that consumes the retire stage's pending link vectors.

Evidence: docs/reconstruction/LINK_SOLVER.md, "Pair link worker" (callback thunk
RVA 0x18df760 -> body 0x18ddd30), "Recycled link acquire" (0x18ddf60) and the
pair handlers 0x18df770 (dynamic), 0x18df910 (static) and 0x18e0a60 (flagged).

Recovered local behavior only. The provider slot owners that 0x18de440 fills are
per-worker job contexts. The vector at owner+0x28 that retire appends to is a
free list of recycled link objects: this worker pops from it (0x18ddf60) whenever
a body pair needs a new link, destroys the old object through its vtable, then
reinitializes it in place. New links are appended to the worker's own vector at
owner+8 for the later merge (0x18df4e0, not reconstructed here).

Field names, the flat-memory helper and the services object are authored design
choices. Contact generation (0x18dd400), contact-flag refresh (0x18dde70), held
release (0x18de3e0), external contacts (0x18e0ad0), the pair filter (0x18deb70),
the two flagged-pair handlers (0x18dfa10, 0x18e01e0), the frame scratch arena
(0x18c9140/0x18c8f50), the link destructor, the protected pool refill
(0x18de1e0), the global serial counter and the allocator are supplied services.
"""
import bisect
import struct

from engine.pose_body_connectivity_retire import reserve_pose_pointer_vector

PAIR_SCRATCH_BYTES = 0x5dc0
LINK_REFILL_COUNT = 5
NEW_LINK_VECTOR_TAG = 0x25
# Image addresses written by the in-place constructor (evidence anchors only;
# build specific, not portable identifiers).
LINK_BASE_VTABLE = 0x1429c9fd0
LINK_VTABLE = 0x1429c9fd8
DYNAMIC_KINDS = (1, 0x8002)


class PoseFlatMemory:
    """Authored sparse little-endian memory: base address -> bytearray."""

    def __init__(self, regions=None):
        self.regions = {}
        self._bases = []
        for base, raw in (regions or {}).items():
            self.add(base, raw)

    def add(self, base, raw):
        if base not in self.regions:
            bisect.insort(self._bases, base)
        self.regions[base] = raw if isinstance(raw, bytearray) else bytearray(raw)
        return self.regions[base]

    def _locate(self, address, size):
        i = bisect.bisect_right(self._bases, address) - 1
        if i >= 0:
            base = self._bases[i]
            raw = self.regions[base]
            if address + size <= base + len(raw):
                return raw, address - base
        raise KeyError('unmapped %#x+%d' % (address, size))

    def view(self, address, size):
        raw, offset = self._locate(address, size)
        return memoryview(raw)[offset:offset + size]

    def get(self, fmt, address):
        raw, offset = self._locate(address, struct.calcsize(fmt))
        return struct.unpack_from(fmt, raw, offset)[0]

    def put(self, fmt, address, value):
        raw, offset = self._locate(address, struct.calcsize(fmt))
        struct.pack_into(fmt, raw, offset, value)

    def q(self, address): return self.get('<Q', address)
    def d(self, address): return self.get('<I', address)
    def i(self, address): return self.get('<i', address)
    def w(self, address): return self.get('<H', address)
    def b(self, address): return self.get('<B', address)
    def set_q(self, address, value): self.put('<Q', address, value & 0xFFFFFFFFFFFFFFFF)
    def set_d(self, address, value): self.put('<I', address, value & 0xFFFFFFFF)
    def set_b(self, address, value): self.put('<B', address, value & 0xFF)


class _RetaggedAllocator:
    """0x18df030 is 0x18def10's body with tag 0x25 instead of 0x28."""

    def __init__(self, inner, tag):
        self.inner = inner
        self.tag = tag

    def allocate(self, size, alignment, _tag):
        return self.inner.allocate(size, alignment, self.tag)

    def reallocate(self, pointer, size, alignment, _tag):
        return self.inner.reallocate(pointer, size, alignment, self.tag)

    def release(self, pointer):
        return self.inner.release(pointer)


def reserve_pose_new_link_vector(descriptor, capacity, *, allocator):
    """0x18df030: pointer-vector reserve, tag 0x25 (otherwise identical to 18def10)."""
    reserve_pose_pointer_vector(descriptor, capacity,
                                allocator=_RetaggedAllocator(allocator, NEW_LINK_VECTOR_TAG))


def _push(mem, vector, value, reserve):
    used, capacity = mem.d(vector + 8), mem.d(vector + 0xC)
    if used == capacity:
        reserve(mem.view(vector, 16), (capacity * 2) & 0xFFFFFFFF if capacity else 8)
    used = mem.d(vector + 8)
    mem.set_q(mem.q(vector) + used * 8, value)
    mem.set_d(vector + 8, used + 1)


def acquire_pose_link(mem, vector, *, allocator, destroy, refill, next_serial,
                      vtables=(LINK_BASE_VTABLE, LINK_VTABLE)):
    """0x18ddf60: pop a recycled link from a pointer vector and reinitialize it.

    vector: pointer q@0, count u32@8, capacity u32@0xC (owner+0x28 in the worker).
    Nonempty: count -= 1, take the last pointer, call destroy(link) (native
    vtable[0](link, 0)), then rebuild fields in place; see LINK_SOLVER.md.
    Empty: reserve max(count+5, 2*capacity) through 0x18def10 when count+5 exceeds
    capacity, add 5 to count, call refill(element_address, 5) (protected pool
    allocation 0x18de1e0), then pop the last pointer without reinitializing it.
    next_serial() returns the prior value of the global link serial counter.
    """
    used = mem.d(vector + 8)
    if used == 0:
        need = (used + LINK_REFILL_COUNT) & 0xFFFFFFFF
        capacity = mem.d(vector + 0xC)
        if need > capacity:
            reserve_pose_pointer_vector(mem.view(vector, 16), max(need, (capacity * 2) & 0xFFFFFFFF),
                                        allocator=allocator)
        elements = mem.q(vector)
        mem.set_d(vector + 8, mem.d(vector + 8) + LINK_REFILL_COUNT)
        refill(elements + used * 8, LINK_REFILL_COUNT)
        mem.set_d(vector + 8, mem.d(vector + 8) - 1)
        return mem.q(mem.q(vector) + mem.d(vector + 8) * 8)
    used -= 1
    mem.set_d(vector + 8, used)
    link = mem.q(mem.q(vector) + used * 8)
    destroy(link)
    for offset in (8, 0x10, 0x18):
        mem.set_q(link + offset, 0)
    mem.set_q(link, vtables[0])
    for offset in (0x20, 0x28, 0x30, 0x38):
        mem.set_q(link + offset, 0)
    mem.set_d(link + 0x40, next_serial())
    mem.set_q(link, vtables[1])
    mem.set_q(link + 0x50, 0)
    mem.set_q(link + 0x58, link + 0x68)      # inline one-entry contact storage
    mem.set_d(link + 0x60, 0)
    mem.set_d(link + 0x64, 1)
    flags = mem.b(link + 0x84)
    mem.set_q(link + 0x78, 0)
    mem.set_d(link + 0x80, 0xFFFFFFFF)
    mem.set_b(link + 0x84, (flags & 0xFD) | 1)
    return link


def find_pose_pair_link(mem, descriptor, key):
    """Unsigned 64-bit search of an indexed tree; returns (index, value) or (-1, None).

    descriptor: node pointer q@0, root index i32@0x14; 32-byte nodes with left
    i32@0, right i32@4, value q@0x10, key q@0x18.
    """
    index = mem.i(descriptor + 0x14)
    nodes = mem.q(descriptor)
    while index != -1:
        node = nodes + index * 32
        node_key = mem.q(node + 0x18)
        if key < node_key:
            index = mem.i(node)
        elif node_key < key:
            index = mem.i(node + 4)
        else:
            return index, mem.q(node + 0x10)
    return -1, None


def _new_pair_link(mem, owner, pair, services):
    link = acquire_pose_link(mem, owner + 0x28, allocator=services.allocator,
                             destroy=services.destroy_link, refill=services.refill_links,
                             next_serial=services.next_serial)
    for offset in (0, 8, 0x10):
        mem.set_q(link + 8 + offset, mem.q(pair + offset))
    return link


def _reserve_new(services):
    return lambda view, capacity: reserve_pose_new_link_vector(view, capacity,
                                                               allocator=services.allocator)


def process_pose_dynamic_pair(mem, owner, pair, services):
    """0x18df770: find or create the pair's link, then run its contact services."""
    first, second = mem.q(pair), mem.q(pair + 8)
    same_group = mem.q(mem.q(first + 0x30) + 0x20) == mem.q(mem.q(second + 0x30) + 0x20)
    index, link = find_pose_pair_link(mem, mem.q(owner) + 8, mem.q(pair + 0x10))
    if index == -1:
        link = _new_pair_link(mem, owner, pair, services)
        mem.set_b(link + 0x84, mem.b(link + 0x84) & 0xFD)
        mem.set_q(link + 0x50, link)
    services.generate_contacts(owner, first, second, link, same_group)
    services.refresh_contact_flag(link)
    if mem.b(first + 0xAA) >= 0x80 or mem.b(second + 0xAA) >= 0x80:
        services.external_contacts(owner, first, second, link)
    elif mem.q(link + 0x78):
        services.release_held(link)
    accepted = services.filter(mem.q(owner), link)
    if not accepted:
        if index != -1:
            mem.set_b(link + 0x84, mem.b(link + 0x84) & 0xFE)
            return
        mem.set_b(link + 0x84, mem.b(link + 0x84) | 2)
    elif index != -1:
        return
    _push(mem, owner + 8, link, _reserve_new(services))


def process_pose_static_pair(mem, owner, pair, services):
    """0x18df910: create a flag-2 link for an unseen pair without contact work."""
    first = mem.q(pair)
    if mem.w(mem.q(first + 0x30) + 0x50) == 0x8002:
        if mem.w(mem.q(mem.q(pair + 8) + 0x30) + 0x50) == 4:
            return
    index, _ = find_pose_pair_link(mem, mem.q(owner) + 8, mem.q(pair + 0x10))
    if index != -1:
        return
    link = _new_pair_link(mem, owner, pair, services)
    mem.set_b(link + 0x84, mem.b(link + 0x84) | 2)
    mem.set_q(link + 0x50, link)
    _push(mem, owner + 8, link, _reserve_new(services))


def route_pose_flagged_pair(mem, owner, pair, services):
    """0x18e0a60: route by presence of the key in the provider+0x38 tree."""
    index, _ = find_pose_pair_link(mem, mem.q(owner) + 0x38, mem.q(pair + 0x10))
    if index == -1:
        services.create_neighbor(owner, pair)      # 0x18e01e0
    else:
        services.update_neighbor(owner, pair)      # 0x18dfa10


def claim_pose_pair_serial(mem, provider):
    """Single-thread stand-in for lock xadd [provider+0x17c], 1; not atomic."""
    old = mem.d(provider + 0x17C)
    mem.set_d(provider + 0x17C, old + 1)
    return old


def _dynamic(mem, kind_record):
    return mem.w(kind_record + 0x50) in DYNAMIC_KINDS


def run_pose_pair_worker(mem, owner, services, *, claim=claim_pose_pair_serial,
                         dynamic=process_pose_dynamic_pair, static=process_pose_static_pair,
                         flagged=route_pose_flagged_pair):
    """0x18df760 -> 0x18ddd30: claim 24-byte pairs from the provider until exhausted.

    owner is the worker context from provider+0x70[slot]; owner+0 holds the
    provider. The dispatcher's caller-thread flag is not read. Pairs are
    (first body q, second body q, key q) at provider+0x170, count u32 @0x178,
    shared claim cursor u32 @0x17c. claim(mem, provider) returns the prior cursor.
    """
    mem.set_d(owner + 0x10, 0)
    mem.set_d(owner + 0x20, 0)
    mem.set_q(owner + 0x58, services.scratch_allocate(PAIR_SCRATCH_BYTES))
    mem.set_d(owner + 0x60, PAIR_SCRATCH_BYTES)
    index = claim(mem, mem.q(owner))
    while index < mem.d(mem.q(owner) + 0x178):
        pair = mem.q(mem.q(owner) + 0x170) + index * 24
        first, second = mem.q(pair), mem.q(pair + 8)
        first_kind, second_kind = mem.q(first + 0x30), mem.q(second + 0x30)
        if _dynamic(mem, first_kind) and _dynamic(mem, second_kind):
            if mem.w(first + 0xC0) and mem.w(second + 0xC0):
                if mem.b(first_kind + 0x52) & 4 or mem.b(second_kind + 0x52) & 4:
                    flagged(mem, owner, pair, services)
                else:
                    dynamic(mem, owner, pair, services)
        else:
            static(mem, owner, pair, services)
        index = claim(mem, mem.q(owner))
    services.scratch_release(mem.q(owner + 0x58))
    mem.set_q(owner + 0x58, 0)
    mem.set_d(owner + 0x60, 0)
