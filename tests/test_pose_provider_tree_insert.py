import random
import struct
import unittest

from engine.pose_body_tree import _Tree
from engine.pose_pair_link_merge import merge_pose_neighbor_records, merge_pose_new_links
from engine.pose_pair_link_worker import PoseFlatMemory
from engine.pose_provider_tree_insert import (LINK_TREE_TAG, NEIGHBOR_TREE_TAG, insert_pose_link_tree,
                                              insert_pose_neighbor_tree)
try:
    from tests.test_pose_pair_link_merge import Svc, fixture
except ImportError:
    from test_pose_pair_link_merge import Svc, fixture


class Alloc:
    def __init__(self, mem):
        self.mem, self.next, self.sizes, self.log = mem, 0x200000, {}, []

    def _new(self, size):
        p = self.next
        self.next += size + 0x10
        self.mem.add(p, bytearray(size))
        self.sizes[p] = size
        return p

    def allocate(self, size, align, tag):
        self.log.append(('alloc', size, align, tag))
        return self._new(size)

    def reallocate(self, ptr, size, align, tag):
        self.log.append(('realloc', ptr, size, align, tag))
        n = self._new(size)
        k = min(self.sizes[ptr], size)
        self.mem.view(n, k)[:] = bytes(self.mem.view(ptr, k))
        return n

    def release(self, ptr):
        self.log.append(('free', ptr))


T = 0x1000


def empty_tree(mem, cap=0):
    d = mem.add(T, bytearray(0x40))
    ptr = 0
    if cap:
        ptr = 0x8000
        mem.add(ptr, bytearray(cap * 32))
    struct.pack_into('<QIIIii', d, 0, ptr, 0, 0, cap, -1, -1)
    return d


def check(mem, tree=T):
    d = mem.view(tree, 0x20)
    ptr, active, free, cap, root, head = struct.unpack_from('<QIIIii', d, 0)
    nodes = mem.view(ptr, cap * 32)
    seen = []

    def walk(i, parent, lo, hi):
        if i == -1:
            return 1
        l, r, p = struct.unpack_from('<iii', nodes, i * 32)
        k = struct.unpack_from('<Q', nodes, i * 32 + 24)[0]
        assert p == parent and (lo is None or k > lo) and (hi is None or k < hi)
        red = nodes[i * 32 + 12]
        if red:
            assert all(c == -1 or nodes[c * 32 + 12] == 0 for c in (l, r))
        a = walk(l, i, lo, k)
        seen.append(k)
        b = walk(r, i, k, hi)
        assert a == b
        return a + (0 if red else 1)

    if root != -1:
        assert nodes[root * 32 + 12] == 0
    walk(root, -1, None, None)
    assert len(seen) == active
    return seen


class InsertTests(unittest.TestCase):
    def test_first_insert_allocates_four_and_roots_black(self):
        mem = PoseFlatMemory(); empty_tree(mem); a = Alloc(mem)
        self.assertTrue(insert_pose_link_tree(mem, T, 7, 0xAA, allocator=a))
        self.assertEqual(a.log, [('alloc', 128, 0x10, LINK_TREE_TAG)])
        ptr, active, free, cap, root, head = struct.unpack_from('<QIIIii', mem.view(T, 0x20), 0)
        self.assertEqual((active, free, cap, root, head), (1, 0, 4, 0, -1))
        node = mem.view(ptr, 32)
        self.assertEqual(struct.unpack_from('<iiiBBHQQ', node, 0), (-1, -1, -1, 0, 0, 0, 0xAA, 7))

    def test_neighbor_variant_uses_other_tag_and_doubles(self):
        mem = PoseFlatMemory(); empty_tree(mem, 2); a = Alloc(mem)
        a.sizes[0x8000] = 64
        for k in (5, 3, 9):
            insert_pose_neighbor_tree(mem, T, k, k, allocator=a)
        self.assertEqual(a.log[0][0], 'realloc')
        self.assertEqual(a.log[0][2:], (128, 0x10, NEIGHBOR_TREE_TAG))
        self.assertEqual(check(mem), [3, 5, 9])

    def test_duplicate_is_rejected_without_growth_or_write(self):
        mem = PoseFlatMemory(); empty_tree(mem, 2); a = Alloc(mem)
        for k in (1, 2):
            insert_pose_link_tree(mem, T, k, k, allocator=a)
        before = (bytes(mem.view(T, 0x20)), bytes(mem.view(0x8000, 64)))
        a.log.clear()
        self.assertFalse(insert_pose_link_tree(mem, T, 2, 0x99, allocator=a))   # full tree, duplicate: no grow
        self.assertEqual(a.log, [])
        self.assertEqual((bytes(mem.view(T, 0x20)), bytes(mem.view(0x8000, 64))), before)

    def test_free_list_slot_is_reused_before_append(self):
        mem = PoseFlatMemory(); empty_tree(mem, 8); a = Alloc(mem)
        for k in range(1, 6):
            insert_pose_link_tree(mem, T, k, k, allocator=a)
        d = mem.view(T, 0x20); nodes = mem.view(0x8000, 256)
        slot = [i for i in range(5) if struct.unpack_from('<Q', nodes, i * 32 + 24)[0] == 2][0]
        a.log.clear()
        _Tree(d, nodes).remove(slot, 8)
        head = struct.unpack_from('<i', d, 0x18)[0]
        self.assertNotEqual(head, -1)
        self.assertEqual(struct.unpack_from('<II', d, 8), (4, 1))
        insert_pose_link_tree(mem, T, 100, 1, allocator=a)
        self.assertEqual(struct.unpack_from('<Q', nodes, head * 32 + 24)[0], 100)   # the freed slot, not slot 5
        self.assertEqual(struct.unpack_from('<IIi', d, 8), (5, 0, 8))
        self.assertEqual(struct.unpack_from('<i', d, 0x18)[0], -1)
        self.assertEqual(a.log, [])
        self.assertEqual(check(mem), [1, 3, 4, 5, 100])

    def test_unsigned_keys_and_random_validity_with_growth(self):
        rng = random.Random(7)
        for _ in range(60):
            mem = PoseFlatMemory(); empty_tree(mem); a = Alloc(mem); keys = set()
            for _ in range(rng.randrange(1, 80)):
                k = rng.choice([rng.randrange(1 << 64), 2 ** 63, 2 ** 63 - 1, 2 ** 64 - 1, 0, rng.randrange(30)])
                self.assertEqual(insert_pose_link_tree(mem, T, k, 0, allocator=a), k not in keys)
                keys.add(k)
                self.assertEqual(sorted(check(mem)), sorted(keys))
        for order in (range(100), range(100, 0, -1)):
            mem = PoseFlatMemory(); empty_tree(mem); a = Alloc(mem)
            for k in order:
                insert_pose_link_tree(mem, T, k, 0, allocator=a)
            self.assertEqual(sorted(check(mem)), sorted(order))


class MergeCompositionTests(unittest.TestCase):
    def test_new_link_merge_populates_provider_tree(self):
        keys = [[40, 10, 30], [20, 50], [60]]
        mem = fixture(keys, 8, 0x10); s = Svc(mem); a = Alloc(mem)
        provider = mem.view(0x1000, 0x200)
        struct.pack_into('<ii', provider, 8 + 0x14, -1, -1)       # provider+8 tree: root, free head empty
        ins = lambda tree, key, value: insert_pose_link_tree(mem, tree, key, value, allocator=a)
        merge_pose_new_links(mem, 0x1000, 3, reserve=s.reserve, copy=s.copy, sort=s.sort, attach=s.attach, insert=ins)
        self.assertEqual(check(mem, 0x1000 + 8), [10, 20, 30, 40, 50, 60])
        d = mem.view(0x1000 + 8, 0x20)
        ptr, _, _, cap, root, _ = struct.unpack_from('<QIIIii', d, 0)
        for i in range(6):                                          # value qword = the link pointer
            k = struct.unpack_from('<Q', mem.view(ptr + i * 32, 32), 0x18)[0]
            self.assertIn(struct.unpack_from('<Q', mem.view(ptr + i * 32, 32), 0x10)[0] , [0x40000 + 0x100 * j for j in range(6)])
        self.assertEqual(cap, 8)                                    # 4 -> 8 doubling while inserting six

    def test_neighbor_record_merge_populates_neighbor_tree_with_duplicates_ignored(self):
        mem = fixture([[5, 7], [5, 9]], 0x18, 0x20); s = Svc(mem); a = Alloc(mem)
        provider = mem.view(0x1000, 0x200)
        struct.pack_into('<ii', provider, 0x38 + 0x14, -1, -1)
        ins = lambda tree, key, value: insert_pose_neighbor_tree(mem, tree, key, value, allocator=a)
        merge_pose_neighbor_records(mem, 0x1000, 2, reserve=s.reserve, copy=s.copy, attach=s.attach, insert=ins, finish=s.finish)
        self.assertEqual(check(mem, 0x1000 + 0x38), [5, 7, 9])
        self.assertTrue(all(e[3] == NEIGHBOR_TREE_TAG for e in a.log))


if __name__ == '__main__':
    unittest.main()
