import struct
import unittest

from engine.pose_link_held_release import release_pose_link_held
from engine.pose_pair_link_worker import PoseFlatMemory


class PoseLinkHeldReleaseTests(unittest.TestCase):
    LINK = 0x1000
    POOL = 0x2000
    GUARD = 0x9000

    def make_memory(self, held, head, count):
        link = bytearray(0x90)
        struct.pack_into('<Q', link, 0x78, held)
        pool = bytearray(0x40)
        struct.pack_into('<I', pool, 0x28, count)
        struct.pack_into('<Q', pool, 0x30, head)
        regions = {self.LINK: link, self.POOL: pool, 0x3000: bytearray(0x40)}
        if held:
            token = bytearray(0x40)
            struct.pack_into('<Q', token, 0, 0xDEAD)
            regions[held] = token
        return PoseFlatMemory(regions)

    def release(self, mem):
        log = []
        token = release_pose_link_held(
            mem, self.LINK,
            enter_guard=lambda g: log.append(('enter', g, mem.q(self.LINK + 0x78))),
            leave_guard=lambda g, p: log.append(('leave', g, p)),
            guard=self.GUARD, pool=self.POOL)
        return token, log

    def test_pushes_token_onto_pool_free_list_and_clears_link(self):
        held, head = 0x5000, 0x3000
        mem = self.make_memory(held, head, 7)
        token, log = self.release(mem)
        self.assertEqual(token, held)
        self.assertEqual(mem.q(held), head)                 # token.next = old head
        self.assertEqual(mem.q(self.POOL + 0x30), held)     # pool head = token
        self.assertEqual(mem.d(self.POOL + 0x28), 6)        # live count decremented
        self.assertEqual(mem.q(self.LINK + 0x78), 0)
        self.assertEqual(log, [('enter', self.GUARD, held), ('leave', self.GUARD, self.POOL)])

    def test_successive_releases_are_lifo(self):
        first, second = 0x5000, 0x5100
        mem = self.make_memory(first, 0, 2)
        mem.add(second, bytearray(0x40))
        self.release(mem)
        mem.set_q(self.LINK + 0x78, second)
        self.release(mem)
        self.assertEqual(mem.q(self.POOL + 0x30), second)
        self.assertEqual(mem.q(second), first)
        self.assertEqual(mem.d(self.POOL + 0x28), 0)

    def test_count_at_zero_wraps_like_the_native_decrement(self):
        held = 0x5000
        mem = self.make_memory(held, 0, 0)
        self.release(mem)
        self.assertEqual(mem.d(self.POOL + 0x28), 0xFFFFFFFF)

    def test_null_token_raises_after_enter_and_before_any_pool_write(self):
        mem = self.make_memory(0, 0x3000, 4)
        before = (bytes(mem.regions[self.POOL]), bytes(mem.regions[self.LINK]))
        log = []
        with self.assertRaises(ValueError):
            release_pose_link_held(mem, self.LINK,
                                   enter_guard=lambda g: log.append(('enter', g)),
                                   leave_guard=lambda g, p: log.append(('leave', g)),
                                   guard=self.GUARD, pool=self.POOL)
        self.assertEqual(log, [('enter', self.GUARD)])
        self.assertEqual((bytes(mem.regions[self.POOL]), bytes(mem.regions[self.LINK])), before)


if __name__ == '__main__':
    unittest.main()
