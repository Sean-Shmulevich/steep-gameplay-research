"""Post-dispatch merges that follow the pair link jobs.

Evidence: docs/reconstruction/LINK_SOLVER.md, "Pair link job orchestration"
(18ddc40 calls these two last) and the static lead for each. Offsets are evidence
anchors from RVA 0x18df4e0 (new-link merge), 0x18df4a0 (its sort comparator) and
0x18df630 (neighbor-record merge, ends in a tail jump to 0x18dea90).

Recovered local control flow only. Each merge sums the per-worker vectors in the
provider slot table (slot owners at provider+0x70), grows the provider's own
pointer vector, concatenates the worker vectors into it, then walks the result
and registers every entry. Supplied services: the vector reserve (0x18defa0 /
0x18df0c0), the memory copy (0x1c6afb0), the 8-byte-element sort (0x1c8fd50), the
ring attach (0x195c170), the tree inserts (0x18de6a0 / 0x18de830) and the final
neighbor-tree walk (0x18dea90). The comparator 0x18df4a0 is reconstructed.

Memory is any object with q/d/set_q/set_d (for example PoseFlatMemory).
"""
import struct

LINK_COMPARATOR = 0x1418df4a0     # image address handed to the sort (evidence anchor)
RESERVE_TAG_LINKS = 0x22          # 0x18defa0 = 0x18def10 body with tag 0x22
RESERVE_TAG_NEIGHBORS = 0x24      # 0x18df0c0 = 0x18def10 body with tag 0x24
_M32 = 0xFFFFFFFF


class _TaggedAllocator:
    def __init__(self, inner, tag):
        self.inner, self.tag = inner, tag

    def allocate(self, size, alignment, _tag):
        return self.inner.allocate(size, alignment, self.tag)

    def reallocate(self, pointer, size, alignment, _tag):
        return self.inner.reallocate(pointer, size, alignment, self.tag)

    def release(self, pointer):
        return self.inner.release(pointer)


def reserve_pose_link_merge_vector(descriptor, capacity, *, allocator):
    """0x18defa0: pointer-vector reserve with tag 0x22."""
    from engine.pose_body_connectivity_retire import reserve_pose_pointer_vector
    reserve_pose_pointer_vector(descriptor, capacity, allocator=_TaggedAllocator(allocator, RESERVE_TAG_LINKS))


def reserve_pose_neighbor_merge_vector(descriptor, capacity, *, allocator):
    """0x18df0c0: pointer-vector reserve with tag 0x24."""
    from engine.pose_body_connectivity_retire import reserve_pose_pointer_vector
    reserve_pose_pointer_vector(descriptor, capacity, allocator=_TaggedAllocator(allocator, RESERVE_TAG_NEIGHBORS))


def compare_pose_link_order(mem, first_link, second_link):
    """0x18df4a0 on two link pointers a, b: signed 32-bit result.

    Primary key is body kind +0x54 of the link's first body (link+8 -> body+0x30),
    a minus b; if equal, the same for the second body (link+0x10). The native
    comparator receives pointers to the array elements and loads the links itself.
    """
    for offset in (8, 0x10):
        ka = mem.d(mem.q(mem.q(first_link + offset) + 0x30) + 0x54)
        kb = mem.d(mem.q(mem.q(second_link + offset) + 0x30) + 0x54)
        diff = (ka - kb) & _M32
        if diff:
            return diff - (1 << 32) if diff & 0x80000000 else diff
    return 0


def _grown_capacity(total, capacity):
    """Capacity request: total, or the least doubling of the old capacity >= total."""
    if capacity == 0:
        return total
    new = capacity
    while total > new:
        new = (new + new) & _M32
        if new == 0:
            raise OverflowError('native doubling loop never terminates (capacity wraps to 0)')
    return new


def _merge(mem, provider, workers, *, count_off, dst_off, reserve, copy):
    """Shared body: sum, grow, concatenate. Returns nothing; provider vector updated.

    Worker vector pointer is at slot owner +count_off-8, count at +count_off.
    dst_off is the provider vector (pointer, count +8, capacity +0xC).
    """
    total = 0
    for i in range(workers):
        total = (total + mem.d(mem.q(provider + 0x70 + 8 * i) + count_off)) & _M32
    mem.set_d(provider + dst_off + 8, 0)
    capacity = mem.d(provider + dst_off + 0xC)
    if total > capacity:
        reserve(provider + dst_off, _grown_capacity(total, capacity))
    mem.set_d(provider + dst_off + 8, total)
    dst = mem.q(provider + dst_off)
    for i in range(workers):
        owner = mem.q(provider + 0x70 + 8 * i)
        size = (mem.d(owner + count_off) << 3) & 0xFFFFFFFFFFFFFFFF
        copy(dst, mem.q(owner + count_off - 8), size)
        dst = (dst + size) & 0xFFFFFFFFFFFFFFFF


def _entry_key(mem, entry):
    # native: rax = entry + 8 if entry else 0; key = qword [rax + 0x10]
    return mem.q((entry + 8 if entry else 0) + 0x10)


def merge_pose_new_links(mem, provider, workers, *, reserve, copy, sort, attach, insert):
    """0x18df4e0(provider, workers).

    Concatenate every owner+8 link vector (count owner+0x10) into provider+0x28
    (count +0x30, capacity +0x34), sort with the 8-byte comparator, then for each
    entry: attach(link, 1) (0x195c170), then insert(provider+8, key, link) with
    key = qword at link+0x18 (0x18de6a0). Pointer and count are reread every pass.
    Services: reserve(descriptor_address, capacity); copy(dst, src, nbytes);
    sort(base, count, element_size=8, comparator); attach(link, selector);
    insert(tree_address, key, link).
    """
    _merge(mem, provider, workers, count_off=0x10, dst_off=0x28, reserve=reserve, copy=copy)
    sort(mem.q(provider + 0x28), mem.d(provider + 0x30), 8, LINK_COMPARATOR)
    i = 0
    while i < mem.d(provider + 0x30):
        link = mem.q(mem.q(provider + 0x28) + 8 * i)
        attach(link, 1)
        insert(provider + 8, _entry_key(mem, link), link)
        i += 1


def merge_pose_neighbor_records(mem, provider, workers, *, reserve, copy, attach, insert, finish):
    """0x18df630(provider, workers), ending in a tail jump to 0x18dea90(provider).

    Concatenate every owner+0x18 vector (count owner+0x20) into provider+0x58
    (count +0x60, capacity +0x64), unsorted. For each entry: attach(record, 0),
    then insert(provider+0x38, key, record) with key = qword at record+0x18
    (0x18de830). Finally finish(provider).
    """
    _merge(mem, provider, workers, count_off=0x20, dst_off=0x58, reserve=reserve, copy=copy)
    i = 0
    while i < mem.d(provider + 0x60):
        record = mem.q(mem.q(provider + 0x58) + 8 * i)
        attach(record, 0)
        insert(provider + 0x38, _entry_key(mem, record), record)
        i += 1
    finish(provider)
