"""Return of a link's held payload token to its pool free list (RVA 0x18de3e0).

Evidence: docs/reconstruction/LINK_SOLVER.md, "Pair link worker" (dynamic handler 0x18df770
calls release_held(link) when the link holds a token at +0x78 and the pair is not external),
and "Link state reset before provider queue handling" (the same pool-return pattern).

Recovered local behavior, in order:

1. token = link.+0x78 (read before any service call).
2. enter_guard(guard) with the guard global (image 0x143336ab0). Protected thunk 0x143d0ad5d.
3. token.+0 = pool.+0x30 (old free-list head); pool.+0x28 -= 1 (32-bit); pool.+0x30 = token.
   The pool object is the pointer at global 0x143336aa8, read after step 2.
4. leave_guard(guard, pool) with the same guard global and the pool pointer. Protected thunk
   0x143d1de3a.
5. link.+0x78 = 0.

A zero token faults natively at the store in step 3 (write to address 0). The model raises
ValueError at that same point, after step 2 and before any pool mutation. The caller only
calls this routine when +0x78 is nonzero.

Supplied services: enter_guard and leave_guard (both protected, obfuscated thunks). The
free-list push is native code and is reconstructed here, not supplied. The guard value is
the same global for enter and leave, so the caller passes it once.
"""

LINK_HELD_OFFSET = 0x78
POOL_COUNT_OFFSET = 0x28
POOL_HEAD_OFFSET = 0x30


def release_pose_link_held(mem, link, *, enter_guard, leave_guard, guard, pool):
    """Push link's held token onto pool's free list and clear +0x78.

    Returns the token that was released. Raises ValueError for a zero token (native fault).
    """
    token = mem.q(link + LINK_HELD_OFFSET)
    enter_guard(guard)
    if token == 0:
        raise ValueError('held token is null; the native store at token+0 faults')
    mem.set_q(token, mem.q(pool + POOL_HEAD_OFFSET))
    mem.set_d(pool + POOL_COUNT_OFFSET, mem.d(pool + POOL_COUNT_OFFSET) - 1)
    mem.set_q(pool + POOL_HEAD_OFFSET, token)
    leave_guard(guard, pool)
    mem.set_q(link + LINK_HELD_OFFSET, 0)
    return token
