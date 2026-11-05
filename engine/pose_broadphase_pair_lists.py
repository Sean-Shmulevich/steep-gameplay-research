"""Broadphase pair-list accessors read by the per-step controller update.

Evidence: docs/reconstruction/LINK_SOLVER.md, "Broadphase pair lists".

The object at controller+0x28 (controller ctor RVA 0x18b8150, store at
0x18b8172) is the "Dynamic tree multi-threaded broad phase" instance built by
0x193f450 (vtable RVA 0x29ca8a0, size 0xb10). Both controller factories
(0x18ae130 and 0x18b64f4) construct it through 0x193f450 and nothing else
calls that constructor, so this vtable is the one installed. The controller
update 0x18b8fa0 calls four of its virtual slots:

  slot 0x40 (RVA 0x1940410): mov rax,[rcx+0xf8]; mov eax,[rax+8]; ret
  slot 0x48 (RVA 0x1940400): mov rax,[rcx+0xf8]; mov rax,[rax];   ret
  slot 0x60 (RVA 0x19403f0): mov eax,[rcx+0x120]; ret
  slot 0x68 (RVA 0x19403e0): mov rax,[rcx+0x118]; ret

The +0xf8 field is a pointer to one of two vector headers {data, count, cap}
at object+0xd8 and +0xe8 (the base constructor 0x199a760 stores both; step
0x199c880 swaps +0xf8 and +0x100 each step, so the current header alternates).
The +0x118 list is stored inline in the object: data at +0x118, count at
+0x120, capacity at +0x124. Both lists hold 24-byte pair rows.

Offsets are evidence anchors for this build, not portable API fields. The
authored parts are the flat-memory callback and the row decoder; the
accessors themselves are recovered.
"""
import struct

PAIR_ROW_BYTES = 0x18

OFF_ADDED_HEADER = 0xF8      # pointer to a {data, count, cap} vector header
OFF_REMOVED_DATA = 0x118
OFF_REMOVED_COUNT = 0x120

# Evidence anchors: vtable slot offsets and getter RVAs.
VTABLE_RVA = 0x29CA8A0
SLOT_ADDED_COUNT, SLOT_ADDED_ARRAY = 0x40, 0x48
SLOT_REMOVED_COUNT, SLOT_REMOVED_ARRAY = 0x60, 0x68


def _u32(buf, off):
    return struct.unpack_from('<I', buf, off)[0]


def _u64(buf, off):
    return struct.unpack_from('<Q', buf, off)[0]


def added_pair_count(obj, read):
    """Slot 0x40: u32 count of the current added-pairs header.

    obj is the broadphase object bytes; read(address, size) returns bytes at a
    target address (the header lives elsewhere in the object or the heap).
    """
    header = _u64(obj, OFF_ADDED_HEADER)
    return _u32(read(header + 8, 4), 0)


def added_pair_array(obj, read):
    """Slot 0x48: data pointer of the current added-pairs header."""
    header = _u64(obj, OFF_ADDED_HEADER)
    return _u64(read(header, 8), 0)


def removed_pair_count(obj):
    """Slot 0x60: u32 count stored inline at object+0x120."""
    return _u32(obj, OFF_REMOVED_COUNT)


def removed_pair_array(obj):
    """Slot 0x68: data pointer stored inline at object+0x118."""
    return _u64(obj, OFF_REMOVED_DATA)


def decode_pair_rows(read, array, count):
    """Decode 24-byte rows: (first body ptr, second body ptr, 64-bit key).

    Evidence: 0x18ddd30 indexes rows as index*3*8 and reads +0/+8 as the two
    bodies; 0x18dedf0 steps rows by 0x18 and reads +0 (body) and +0x10 (key);
    the append helper 0x199b590 writes 16 bytes then 8 bytes per row.
    """
    rows = []
    for i in range(count):
        raw = read(array + i * PAIR_ROW_BYTES, PAIR_ROW_BYTES)
        rows.append(struct.unpack('<QQQ', raw))
    return rows


def controller_pair_lists(obj, read):
    """What 0x18b8fa0 gathers: (removed rows, added rows), in call order."""
    removed = decode_pair_rows(read, removed_pair_array(obj), removed_pair_count(obj))
    added = decode_pair_rows(read, added_pair_array(obj, read), added_pair_count(obj, read))
    return removed, added
