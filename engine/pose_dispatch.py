"""Recovered synchronous dispatcher policy with supplied concurrency services.

Evidence: LINK_SOLVER.md, Dispatcher claim and completion counters.
"""
import struct


def _signed(value):
    value &= 0xffffffff
    return value - 0x100000000 if value & 0x80000000 else value


def dispatch_pose_workers(dispatcher, requested, callback, arguments, *,
                          atomic_compare_exchange, atomic_add, enqueue, take,
                          invoke, notify, wait):
    """Run dispatch against explicit shared storage and synchronization services.

    atomic_compare_exchange(offset, expected, desired) returns the prior uint32;
    atomic_add(offset, delta) likewise returns the prior value. Both operate on
    dispatcher. enqueue accepts a (tag, slot, callback, argument) record; take
    returns one or None. invoke(callback, argument, True) runs on the calling
    thread. notify(handle) and wait() supply the opaque platform paths.
    arguments is an existing pointer table, or None for null arguments.

    Admission failures raise authored errors rather than reproducing native
    underflow/out-of-range accesses. Exceptions do not unwind submitted jobs.
    """
    if type(requested) is not int or not 0 <= requested <= 0xffffffff:
        raise ValueError('Unsigned worker request required')
    workers = min(requested, struct.unpack_from('<I', dispatcher, 0x10)[0])
    if not workers:
        raise ValueError('Dispatcher requires at least one admitted worker')
    def argument(index):
        return arguments[index] if arguments is not None else 0
    if workers == 1:
        invoke(callback, argument(0), True)
        return
    slot = None
    for candidate in range(32):
        if atomic_compare_exchange(0x6a8 + 4*candidate, 0, workers-1) == 0:
            slot = candidate
            struct.pack_into('<I', dispatcher, 0x628+4*slot, workers-1)
            break
    if slot is None:
        raise ValueError('No free dispatcher completion slot')
    for index in range(1, workers):
        enqueue((0x1de3f0c7, slot, callback, argument(index)))
        handle = struct.unpack_from('<Q', dispatcher, 0x118+8*index)[0]
        notify(handle)
    invoke(callback, argument(0), True)
    while _signed(atomic_add(0x628+4*slot, 0)) > 0:
        record = take()
        if record is None:
            break
        tag, owner_slot, function, token = record
        # The caller-help path does not inspect tag, and can help another slot.
        atomic_add(0x628+4*owner_slot, -1)
        invoke(function, token, True)
        atomic_add(0x6a8+4*owner_slot, -1)
    while _signed(atomic_add(0x6a8+4*slot, 0)) > 0:
        wait()


def pose_dispatch_serial_atomics(dispatcher):
    """Single-thread test adapter only; not atomic under concurrent callers."""
    def compare_exchange(offset, expected, desired):
        old = struct.unpack_from('<I', dispatcher, offset)[0]
        if old == expected:
            struct.pack_into('<I', dispatcher, offset, desired & 0xffffffff)
        return old
    def add(offset, delta):
        old = struct.unpack_from('<I', dispatcher, offset)[0]
        struct.pack_into('<I', dispatcher, offset, (old+delta)&0xffffffff)
        return old
    return compare_exchange, add
