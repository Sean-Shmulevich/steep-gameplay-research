"""Recovered narrow-phase provider tree inserts 0x18de6a0 and 0x18de830.

Evidence: LINK_SOLVER.md "Pair link merges"; disassembly of 0x18de6a0 / 0x18de830
(identical bodies), the grow helpers 0x18df350 (allocator tag 0x21) and 0x18df3f0
(tag 0x23), and the shared red-black insert fixup 0x19a3d40, which ends in tail
jumps to the rotations 0x1959bb0 (left) and 0x18da970 (right).

Trees are the 32-byte-node indexed red-black trees of pose_body_tree.py, here with
the 8-byte unsigned key at node+0x18 and an 8-byte value at node+0x10 (key_size 8).
Descriptor: node pointer q@0, active u32@8, free u32@0xC, capacity u32@0x10,
root i32@0x14, free-list head i32@0x18.

insert(tree, &key, &value) -> bool:
  descend from the root comparing unsigned 64-bit keys (smaller goes left, larger
  right); an equal key returns false and writes nothing (no growth either);
  otherwise
  if active == capacity: grow to 2*capacity (4 when capacity is 0) via the grow
    helper (max with active, no-op on equal capacity, allocator alloc/realloc/free)
  slot = free-list head if any (free--, head = node.right, new head.left = -1)
        else slot = active
  node: left=right=-1, key, value, red byte=1, free byte=0 (bytes 0xE/0xF and the
  parent word are otherwise as written), active++, link under the last visited
  node (or become root), then fixup(tree, slot).
Fixup is the textbook insert recolor/rotate loop; the final root is painted black
only on the path that reaches the root. Quirks kept: a nonzero red byte counts as
red for the parent test but the uncle must equal 1; the new slot's stale bytes 0xE
and 0xF survive; growth happens only after the duplicate check.

Supplied: the allocator (allocate/reallocate/release with alignment 0x10).
Memory is any object with view(address, size) (for example PoseFlatMemory).
"""
import struct

from engine.pose_body_tree import _Tree

LINK_TREE_TAG = 0x21       # 0x18df350, used by 0x18de6a0
NEIGHBOR_TREE_TAG = 0x23   # 0x18df3f0, used by 0x18de830
ALIGNMENT = 0x10
_M32 = 0xFFFFFFFF


def _grow(descriptor, capacity, tag, allocator):
    """0x18df350 / 0x18df3f0: node-array capacity = max(capacity, active)."""
    active = struct.unpack_from('<I', descriptor, 8)[0]
    capacity = max(capacity & _M32, active)
    if capacity == struct.unpack_from('<I', descriptor, 0x10)[0]:
        return
    pointer = struct.unpack_from('<Q', descriptor, 0)[0]
    size = capacity << 5
    if pointer:
        if capacity:
            pointer = allocator.reallocate(pointer, size, ALIGNMENT, tag)
        else:
            allocator.release(pointer)
            pointer = 0
    else:
        pointer = allocator.allocate(size, ALIGNMENT, tag)
    struct.pack_into('<Q', descriptor, 0, pointer)
    struct.pack_into('<I', descriptor, 0x10, capacity)


def fixup_pose_tree_insert(tree, index):
    """0x19a3d40(tree, index): recolor/rotate after a red leaf insert."""
    parent = tree.link(index, 8)
    if parent == -1:
        tree.paint(index, 0)
        return
    current = index
    while True:
        if tree.n[parent * 32 + 12] == 0:
            return
        grand = tree.link(parent, 8)
        uncle = tree.link(grand, 4) if parent == tree.link(grand, 0) else tree.link(grand, 0)
        if uncle != -1 and tree.n[uncle * 32 + 12] == 1:
            tree.paint(parent, 0)
            tree.paint(uncle, 0)
            tree.paint(grand, 1)
            current = grand
            parent = tree.link(grand, 8)
            if parent == -1:
                tree.paint(current, 0)
                return
            continue
        if current == tree.link(parent, 4) and parent == tree.link(grand, 0):
            tree.rotate(parent, True)       # 0x1959bb0
            current = tree.link(current, 0)
        elif current == tree.link(parent, 0) and parent == tree.link(grand, 4):
            tree.rotate(parent, False)      # 0x18da970
            current = tree.link(current, 4)
        mid = tree.link(current, 8)
        top = tree.link(mid, 8)
        tree.paint(mid, 0)
        tree.paint(top, 1)
        tree.rotate(top, current != tree.link(mid, 0))   # left child -> right rotation
        return


def _insert(mem, tree_address, key, value, tag, allocator):
    descriptor = mem.view(tree_address, 0x20)
    key &= 0xFFFFFFFFFFFFFFFF
    root = struct.unpack_from('<i', descriptor, 0x14)[0]
    parent, went_left = -1, False
    if root != -1:
        pointer = struct.unpack_from('<Q', descriptor, 0)[0]
        cap = struct.unpack_from('<I', descriptor, 0x10)[0]
        nodes = mem.view(pointer, cap * 32)
        current = root
        while True:
            parent = current
            node_key = struct.unpack_from('<Q', nodes, current * 32 + 24)[0]
            if key < node_key:
                went_left, current = True, struct.unpack_from('<i', nodes, current * 32)[0]
            elif node_key < key:
                went_left, current = False, struct.unpack_from('<i', nodes, current * 32 + 4)[0]
            else:
                return False
            if current == -1:
                break
    active = struct.unpack_from('<I', descriptor, 8)[0]
    capacity = struct.unpack_from('<I', descriptor, 0x10)[0]
    if active == capacity:
        _grow(descriptor, (capacity * 2) & _M32 if capacity else 4, tag, allocator)
    pointer = struct.unpack_from('<Q', descriptor, 0)[0]
    capacity = struct.unpack_from('<I', descriptor, 0x10)[0]
    nodes = mem.view(pointer, capacity * 32)
    head = struct.unpack_from('<i', descriptor, 0x18)[0]
    if head != -1:
        slot = head
        free = struct.unpack_from('<I', descriptor, 0xC)[0]
        struct.pack_into('<I', descriptor, 0xC, (free - 1) & _M32)
        head = struct.unpack_from('<i', nodes, slot * 32 + 4)[0]
        struct.pack_into('<i', descriptor, 0x18, head)
        if head != -1:
            struct.pack_into('<i', nodes, head * 32, -1)
    else:
        slot = struct.unpack_from('<I', descriptor, 8)[0]
    base = slot * 32
    struct.pack_into('<ii', nodes, base, -1, -1)
    struct.pack_into('<Q', nodes, base + 0x18, key)
    struct.pack_into('<Q', nodes, base + 0x10, value & 0xFFFFFFFFFFFFFFFF)
    nodes[base + 12] = 1
    nodes[base + 13] = 0
    struct.pack_into('<I', descriptor, 8, (struct.unpack_from('<I', descriptor, 8)[0] + 1) & _M32)
    if parent != -1:
        struct.pack_into('<i', nodes, base + 8, parent)
        struct.pack_into('<i', nodes, parent * 32 + (0 if went_left else 4), slot)
    else:
        struct.pack_into('<i', descriptor, 0x14, slot)
        struct.pack_into('<i', nodes, base + 8, -1)
    fixup_pose_tree_insert(_Tree(descriptor, nodes), slot)
    return True


def insert_pose_link_tree(mem, tree_address, key, value, *, allocator):
    """0x18de6a0(tree, &key, &value): returns True when a node was inserted."""
    return _insert(mem, tree_address, key, value, LINK_TREE_TAG, allocator)


def insert_pose_neighbor_tree(mem, tree_address, key, value, *, allocator):
    """0x18de830(tree, &key, &value): same body, grow tag 0x23."""
    return _insert(mem, tree_address, key, value, NEIGHBOR_TREE_TAG, allocator)
