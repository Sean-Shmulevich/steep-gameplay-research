"""Pool refill of recycled pair-link objects (RVA 0x18de1e0).

Evidence: docs/reconstruction/LINK_SOLVER.md, "Recycled link acquire" (the empty-vector
branch calls the refill with count 5) and "Pair link worker" (owner+0x28 free list).
The refill body itself is 0x18de1e0; its callee layout was read from the disassembly.

Recovered local behavior:

- Entry saves elements (rcx) and count (edx), then calls the protected pool prepare
  thunk 0x143f3608c with the guard global value (image 0x143336ac0) and count. Its
  result is not used.
- The loop runs count times (zero count skips it). Both paths then reach the epilogue at
0x18de2c2, which loads the same guard global (image 0x143336ac0) into rcx, restores rbx and
calls the protected epilogue thunk 0x143f76da2 (leave_guard). Each pass takes one
  object from the pool with 0x1418b5d10 (the pool object is the global at 0x143336ab8).
  A null take stores null and skips construction.
- A non-null object is constructed in place with the same field writes as the
  recycled-link constructor in engine/pose_pair_link_worker.py: vtable 0x1429c9fd0
  then 0x1429c9fd8, contact storage at +0x58 pointing to +0x68 with capacity 1, serial
  at +0x40 from lock xadd on 0x14333683c (prior value), flag +0x84 bit1 cleared and
  bit0 set, +0x80 = 0xffffffff, +0x78 = 0.
- The object pointer is stored at elements[i]; the loop then advances by 8 bytes.

Supplied services (not reconstructed):

- prepare(guard, count): protected pool block 0x143f3608c. Its return site 0x18de1fb holds one
  junk byte (0x62) before the loop test, so the thunk must resume after it.
- take(pool): 0x1418b5d10. Its fast path pops the pool free list, but its slow path is
  not reconstructed, so the whole call is supplied.
- leave_guard(guard): protected epilogue thunk 0x143f76da2, entered with rcx = guard on
  both exit paths.
- next_serial(): the lock xadd on 0x14333683c is native code in the binary. The module
  takes it as a service so a Python reference can mirror the global.

The guard and pool values are passed in by the caller. The native code re-reads the
pool global on every pass; the model reads it once, because no service writes it.
"""
from engine.pose_pair_link_worker import LINK_BASE_VTABLE, LINK_VTABLE

CONTACT_INLINE_OFFSET = 0x68


def construct_pose_link(mem, link, serial):
    """Fields written by 0x18de1e0 for each non-null object (native order)."""
    for offset in (8, 0x10, 0x18):
        mem.set_q(link + offset, 0)
    mem.set_q(link, LINK_BASE_VTABLE)
    for offset in (0x20, 0x28, 0x30, 0x38):
        mem.set_q(link + offset, 0)
    mem.set_d(link + 0x40, serial)
    mem.set_q(link, LINK_VTABLE)
    mem.set_q(link + 0x50, 0)
    mem.set_q(link + 0x58, link + CONTACT_INLINE_OFFSET)
    mem.set_d(link + 0x60, 0)
    mem.set_d(link + 0x64, 1)
    flags = mem.b(link + 0x84)
    mem.set_q(link + 0x78, 0)
    mem.set_d(link + 0x80, 0xFFFFFFFF)
    mem.set_b(link + 0x84, (flags & 0xFD) | 1)


def refill_pose_link_objects(mem, elements, count, *, prepare, take, leave_guard,
                             next_serial, guard, pool):
    """0x18de1e0: fill count slots at elements with pool objects, constructed in place.

    elements: address of the pointer array (the vector tail, element i at +8*i).
    prepare(guard, count), take(pool) and leave_guard(guard) are the supplied services
    described above. A null take stores 0 in the slot and constructs nothing for that slot.
    Returns the number of non-null objects constructed.
    """
    prepare(guard, count)
    constructed = 0
    for i in range(count):
        link = take(pool)
        if link:
            construct_pose_link(mem, link, next_serial())
            constructed += 1
        mem.set_q(elements + 8 * i, link or 0)
    leave_guard(guard)
    return constructed
