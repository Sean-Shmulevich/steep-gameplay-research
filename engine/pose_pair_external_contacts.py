"""External-contacts path of the dynamic pair handler: per-link body snapshot record.

Evidence: native routine RVA 0x18e0ad0, called from 0x18df770 as
`external(owner, first, second, link)` (rcx, rdx, r8, r9) when either body's byte
at +0xAA is >= 0x80. See docs/reconstruction/LINK_SOLVER.md, "Pair link worker"
and "Pair link external contacts".

Recovered behavior: link+0x78 is a lazily created snapshot record (the same slot the
dynamic handler tests before calling the held release 0x18de3e0). If it is null, the
routine enters a guard (obfuscated stub 0x143f4633d, argument [0x143336ab0]), takes a
record from a pool (0x18dd100 on the pool object [0x143336aa8]), leaves the guard
(obfuscated stub 0x14357414d) and stores it at link+0x78. A non-null record is reused
and overwritten in place. Either way it then fills the record from the two bodies:

```text
rec[0x20..0x2c) = first[0x40..0x4c)    rec[0x80..0x8c) = second[0x40..0x4c)
rec[0x30..0x3c) = first[0x50..0x5c)    rec[0x90..0x9c) = second[0x50..0x5c)
rec[0x40..0x4c) = first[0x60..0x6c)    rec[0xa0..0xac) = second[0x60..0x6c)
rec[0x50..0x5c) = first[0x70..0x7c)    rec[0xb0..0xbc) = second[0x70..0x7c)
if first.vtable[1](first, 0x8002):   rec[0x00..0x18) = first[0x1a0..0x1b8)
else:                                rec[0x00..0x18) = 0
if second.vtable[1](second, 0x8002): rec[0x60..0x78) = second[0x1a0..0x1b8)
else:                                rec[0x60..0x78) = 0
```

All copies are 32-bit moves (three dwords per block, six for the 0x1a0 blocks); the
zero fill is three 64-bit stores. Only the low byte of each virtual result counts.
Bytes of the record not listed (0x18..0x20, 0x3c..0x40, 0x5c..0x60, 0x78..0x80,
0xbc..) are neither read nor written. The first body's virtual call happens after the
first body's blocks and before the second body's; the record is stored to the link
before any copying.

Supplied (authored services): guard enter/leave (the stubs are control-flow
obfuscated; each is entered through `push rdi; call` and returns with the pushed
register restored, so they are modelled as an enter/leave pair whose lock semantics
are inferred, not proven), the pool take, and the body virtual query. The size of the
pool record is not recovered here beyond "at least 0xBC bytes". Offsets are evidence
anchors, not portable API fields.
"""

SNAPSHOT_SLOT = 0x78
QUERY_MASK = 0x8002
_FIRST_BLOCKS = ((0x20, 0x40), (0x30, 0x50), (0x40, 0x60), (0x50, 0x70))
_SECOND_BLOCKS = ((0x80, 0x40), (0x90, 0x50), (0xA0, 0x60), (0xB0, 0x70))


def _copy_dwords(mem, dest, source, count=3):
    for i in range(count):
        mem.set_d(dest + 4 * i, mem.d(source + 4 * i))


def _copy_body(mem, record, body, blocks, extra, query):
    for dest, source in blocks:
        _copy_dwords(mem, record + dest, body + source)
    if query(body, QUERY_MASK) & 0xFF:
        _copy_dwords(mem, record + extra, body + 0x1A0, 6)
    else:
        for i in range(3):
            mem.set_q(record + extra + 8 * i, 0)


def external_pose_contacts(mem, owner, first, second, link, *, guard_enter, guard_leave,
                           take_record, query):
    """0x18e0ad0. owner is unused by the native routine (rcx is never read).

    guard_enter() / guard_leave(): the obfuscated stubs; take_record(): pool take
    0x18dd100; query(body, mask): body virtual slot 1, returns rax.
    """
    record = mem.q(link + SNAPSHOT_SLOT)
    if not record:
        guard_enter()
        record = take_record()
        guard_leave()
        mem.set_q(link + SNAPSHOT_SLOT, record)
    _copy_body(mem, record, first, _FIRST_BLOCKS, 0x00, query)
    _copy_body(mem, record, second, _SECOND_BLOCKS, 0x60, query)
