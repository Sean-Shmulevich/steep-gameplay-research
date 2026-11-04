"""Per-worker free-list rebalance used by the pair link job orchestration.

Evidence: docs/reconstruction/LINK_SOLVER.md, "Pair link job orchestration"
(caller RVA 0x18ddc40, callee RVA 0x1989e60, about 370 instructions, no callees).

Recovered local behavior only. The routine receives an array of context
pointers (slot owner + 0x28) and a count n. Each context holds three
pointer vectors laid out at +0x00, +0x10 and +0x20, each {pointer q@0, count
u32@8, capacity u32@0xC}. In the pair link worker these are the recycled link
free list (owner+0x28), a vector at owner+0x38 and the neighbor free list
(owner+0x48). Offsets are evidence anchors, not portable API fields.

Behavior:
  1. For each of the three vectors, sum the counts of all n contexts (32-bit
     wrap) and take limit = sum / n + 1 (unsigned, 32-bit).
  2. For pass p in 0 .. 2n-1 (32-bit): src = ctx[p % n], dst = ctx[(p+1) % n].
     For each vector in order 0, 1, 2: while src.count > limit, pop the last
     pointer from src and push it onto dst. Pushing onto a full dst vector
     (count == capacity) first grows it to 2*capacity (8 when empty) through the
     pointer-vector reserve 0x18def10 (inlined; allocator vtable +8/+0x10/+0x18,
     alignment 0x10, tag 0x28).
The sums and limits are computed once, before any move. Each pass reads the
current counts, so a surplus ripples around the ring and is pushed on at most
once per pass. Zero contexts divides by zero natively; that is not asserted and
raises ZeroDivisionError here.

The allocator is a supplied service (see engine.pose_body_connectivity_retire).
Memory is the authored flat-memory view from engine.pose_pair_link_worker.
"""
from engine.pose_body_connectivity_retire import reserve_pose_pointer_vector

VECTOR_OFFSETS = (0x00, 0x10, 0x20)
_M32 = 0xFFFFFFFF


def _push(mem, vector, value, allocator):
    used, capacity = mem.d(vector + 8), mem.d(vector + 0xC)
    if used == capacity:
        reserve_pose_pointer_vector(mem.view(vector, 16),
                                    ((capacity * 2) & _M32) if capacity else 8, allocator=allocator)
        used = mem.d(vector + 8)
    mem.set_q(mem.q(vector) + used * 8, value)
    mem.set_d(vector + 8, used + 1)


def rebalance_pose_link_free_lists(mem, contexts, count, *, allocator):
    """0x1989e60(contexts, count). contexts: sequence of context addresses (count used)."""
    count &= _M32
    ctx = [contexts[i] for i in range(count)]
    limits = []
    for off in VECTOR_OFFSETS:
        total = sum(mem.d(c + off + 8) for c in ctx) & _M32
        limits.append(((total // count) + 1) & _M32)
    for p in range(0, (2 * count) & _M32):
        src = ctx[p % count]
        dst = ctx[((p + 1) & _M32) % count]
        for off, limit in zip(VECTOR_OFFSETS, limits):
            s, d = src + off, dst + off
            while mem.d(s + 8) > limit:
                used = mem.d(s + 8) - 1
                mem.set_d(s + 8, used)
                _push(mem, d, mem.q(mem.q(s) + used * 8), allocator)
