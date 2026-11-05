"""Kind-6 bounding-tree query: 0x1952b20 with its traversal 0x19507f0 and queue growth 0x1952f20.

Evidence: docs/reconstruction/LINK_SOLVER.md "Kind-6 tree query and mode-2 neighbourhood filter"
(static reads of 0x1952b20, 0x19507f0, 0x1952f20) and "Narrow-phase capsule-terrain (kind 6)
tester" (tree layout). Native comparison: analysis/command-executor-audit/check_pose_terrain6_leaves.py
-> native/snow_host/pose_terrain6_leaves_validation.json.

Recovered local behaviour (names are ours):

- 0x1952b20(tree, aabb, out, capacity) is a wrapper: 0x19507f0(tree, aabb, out, capacity,
  &tree.extent (+0), &tree.minimum (+0xc)). Nodes are read from the pointer at tree+0x18.
- The box words are min xyz at aabb+0 and max xyz at aabb+0xc; extent/minimum/box are
  loaded as 4 lanes and masked with the XYZ mask, so lane 3 never participates.
- Node (12 bytes): bytes 0..2 quantized min, byte 3 flags, bytes 4..6 quantized
  max-from-top, u16 child 0 at +8, u16 child 1 at +0xa. Flag bit 0/1: child 0/1 is a leaf
  (the u16 is a triangle id). Bits 2..4 (static 0x3336cb0 = {4,8,16,0}) select per axis
  child 0 = decoded min / child 1 = parent min (clear: the other way round); bits 5..7
  (0x3336cc0 = {0x20,0x40,0x80,0}) the same for the max. Decode (0x3336cd0 = 1/255 x4):
  lo = ((q * c) * ext) + min, pmax = ext + min (min + ext for the second register node),
  hi = pmax - ((q * c) * ext). A child keeps (ext = max - min, min, u16 node).
- A child is rejected when, on any axis, child max < box min or box max < child min
  (cmpltps: NaN never rejects).
- Two node slots live in registers (A, B; `held` = 0..2) and a FIFO of 0x30-byte entries
  (ext, min, node) on the stack (inline 0x100). The FIFO is append-only with a read
  cursor; it is never compacted, so growth depends on the total number of pushes.
  Loop: held 0 -> pop A, then pop B if the FIFO is not empty, else visit A alone;
  held 1 -> pop B if the FIFO is not empty, else visit A alone; held 2 -> visit A, B.
  A pair visit decodes A then B, computes all four rejections, then handles A.c0, A.c1,
  B.c0, B.c1 in that order; a single visit handles A.c0, A.c1. Each surviving child: a
  leaf writes its u16 id and stops the query once count >= capacity (signed compare
  after the write, so capacity <= 0 still writes one id); an internal child goes to slot
  A if held == 0, slot B if held == 1, otherwise it is pushed. The loop continues while
  the FIFO has unread entries or a slot is held. Register-held children are visited
  before the FIFO, so the order is not a plain breadth-first order.
- 0x1952f20(queue, 2 * capacity) when a push finds count == capacity: the first growth
  allocates newcap * 0x30 bytes (alignment 0x10, tag 0x19) through the global allocator
  slot 1 and copies the entries; later growths reallocate (slot 2). On exit a heap queue
  is freed (slot 3). Allocation is reported in the trace only; it does not change ids.

Float32 lanes follow engine.pose_contact_payload_update (nan_rule 'sse' or 'x87').
The runtime statics are zero in the image; their values are those of their CRT
initializers (0xc8010, 0xc7ff0, 0xc8030), as the native harness installs them.
Authored: the function names, the trace format and the `service` binding.
"""
import struct

from engine.pose_narrowphase_capsule_terrain6 import _u16, _u64, _vec, vadd, vmask, vmul, vsub, bc
from engine.pose_narrowphase_dispatch import _lt

QUERY_RVA = 0x1952B20
TRAVERSE_RVA = 0x19507F0
QUEUE_GROW_RVA = 0x1952F20
INV_255 = 0x3B808081            # 0x3336cd0 (initializer 0xc8030)
MIN_SELECT = (4, 8, 16)         # 0x3336cb0 (initializer 0xc8010)
MAX_SELECT = (0x20, 0x40, 0x80) # 0x3336cc0 (initializer 0xc7ff0)
INLINE_QUEUE = 0x100
QUEUE_ENTRY = 0x30
NODE_STRIDE = 12


def _s32(x):
    x &= 0xFFFFFFFF
    return x - (1 << 32) if x & 0x80000000 else x


def _float_lanes(qbytes):
    """cvtdq2ps of three bytes, lane 3 masked to zero (bit patterns)."""
    return [struct.unpack('<I', struct.pack('<f', float(b)))[0] if b else 0 for b in qbytes] + [0]


def decode_children(mem, nodes, entry, second, r):
    """Child boxes of one register node. entry = (ext, min, node). Returns
    (flags, ids, [(c0min, c0max), (c1min, c1max)]); `second` selects the min + ext order
    the traversal uses for register slot B."""
    ext, mn, node = entry
    addr = nodes + NODE_STRIDE * node
    raw = bytes(mem.view(addr, NODE_STRIDE))
    flags = raw[3]
    ids = struct.unpack_from('<HH', raw, 8)
    qlo, qhi = _float_lanes(raw[0:3]), _float_lanes(raw[4:7])
    pmax = vadd(mn, ext, r) if second else vadd(ext, mn, r)
    c = bc(INV_255)
    dlo = vadd(vmul(vmul(qlo, c, r), ext, r), mn, r)
    dhi = vsub(pmax, vmul(vmul(qhi, c, r), ext, r), r)
    sel_lo = [bool(flags & b) for b in MIN_SELECT] + [False]
    sel_hi = [bool(flags & b) for b in MAX_SELECT] + [False]
    c0min = [d if s else m for d, m, s in zip(dlo, mn, sel_lo)]
    c0max = [d if s else p for d, p, s in zip(dhi, pmax, sel_hi)]
    c1min = [m if s else d for d, m, s in zip(dlo, mn, sel_lo)]
    c1max = [p if s else d for d, p, s in zip(dhi, pmax, sel_hi)]
    return flags, ids, [(c0min, c0max), (c1min, c1max)]


def rejected(box, qmin, qmax):
    cmin, cmax = box
    return any(_lt(cmax[k], qmin[k]) or _lt(qmax[k], cmin[k]) for k in range(3))


def tree_query(mem, tree, aabb_words, capacity, out=None, *, nan_rule='sse', trace=None):
    """0x1952b20(tree, aabb, out, capacity) -> list of u16 triangle ids in write order.

    aabb_words: six uint32 bit patterns (min xyz, max xyz). When `out` is given the ids
    are also written there as u16. trace, when a dict, receives counters and the
    allocation events of 0x1952f20 (('alloc'|'realloc', bytes), ('free',))."""
    r = nan_rule
    cap = _s32(capacity)
    nodes = _u64(mem, tree + 0x18)
    qmin = vmask(list(aabb_words[0:3]) + [0])
    qmax = vmask(list(aabb_words[3:6]) + [0])
    slot = [(vmask(_vec(mem, tree)), vmask(_vec(mem, tree + 0xC)), 0), None]
    held = 1
    queue, head, qcap, on_heap = [], 0, INLINE_QUEUE, False
    ids = []
    t = trace if trace is not None else {}
    t.update(pairs=0, singles=0, pushes=0, growths=[], allocations=[], max_queue=0, stopped_by_capacity=False)

    def place(box, node):
        nonlocal held, qcap, on_heap
        cmin, cmax = box
        entry = (vsub(cmax, cmin, r), cmin, node)
        if held == 0:
            slot[0], held = entry, 1
        elif held == 1:
            slot[1], held = entry, 2
        else:
            if len(queue) == qcap:                       # 0x1952f20(queue, 2 * capacity)
                new = (2 * qcap) & 0xFFFFFFFF
                t['allocations'].append(('realloc' if on_heap else 'alloc', new * QUEUE_ENTRY))
                t['growths'].append((qcap, new))
                qcap, on_heap = new, True
            queue.append(entry)
            t['pushes'] += 1
            t['max_queue'] = max(t['max_queue'], len(queue))

    def visit(entries):
        """Returns True when the capacity stopped the query."""
        nonlocal held
        held = 0
        decoded = [decode_children(mem, nodes, e, i == 1, r) for i, e in enumerate(entries)]
        rej = [[rejected(box, qmin, qmax) for box in boxes] for _, _, boxes in decoded]
        for (flags, child, boxes), rj in zip(decoded, rej):
            for ci in range(2):
                if rj[ci]:
                    continue
                if flags & (1 << ci):
                    ids.append(child[ci])
                    if len(ids) >= cap:
                        t['stopped_by_capacity'] = True
                        return True
                else:
                    place(boxes[ci], child[ci])
        return False

    while True:
        if held == 0:
            slot[0] = queue[head]
            head += 1
        if held == 2 or (held in (0, 1) and head < len(queue)):
            if held != 2:
                slot[1] = queue[head]
                head += 1
            t['pairs'] += 1
            stop = visit([slot[0], slot[1]])
        else:
            t['singles'] += 1
            stop = visit([slot[0]])
        if stop or not (head < len(queue) or held):
            break
    if on_heap:
        t['allocations'].append(('free',))
    if out is not None and ids:
        mem.view(out, 2 * len(ids))[:] = struct.pack('<%dH' % len(ids), *ids)
    return ids


def service(mem, *, nan_rule='sse', traces=None):
    """Bind to the tester's `query(tree_address, aabb_words, capacity) -> ids` signature."""
    def query(tree, aabb_words, capacity):
        tr = {} if traces is not None else None
        ids = tree_query(mem, tree, aabb_words, capacity, nan_rule=nan_rule, trace=tr)
        if traces is not None:
            tr.update(ids=list(ids), capacity=capacity)
            traces.append(tr)
        return ids
    return query
