import struct
import unittest

from engine.pose_link_pool_refill import refill_pose_link_objects
from engine.pose_pair_link_worker import LINK_VTABLE, PoseFlatMemory, acquire_pose_link


class PoseLinkPoolRefillTests(unittest.TestCase):
    ELEMENTS = 0x1000
    GUARD = 0x7000
    POOL = 0x8000

    def make_memory(self, objects):
        regions = {self.ELEMENTS: bytearray(0x100)}
        for address in objects:
            regions[address] = bytearray(b'\xa5' * 0x90)
        return PoseFlatMemory(regions)

    def refill(self, mem, count, takes, serials=None):
        calls = {'prepare': [], 'take': [], 'serial': [], 'leave': []}
        serial_values = iter(serials if serials is not None else range(100, 200))

        def prepare(guard, n):
            calls['prepare'].append((guard, n))

        def take(pool):
            calls['take'].append(pool)
            return takes.pop(0)

        def next_serial():
            value = next(serial_values)
            calls['serial'].append(value)
            return value

        refill_pose_link_objects(mem, self.ELEMENTS, count, prepare=prepare, take=take,
                                 leave_guard=calls['leave'].append,
                                 next_serial=next_serial, guard=self.GUARD, pool=self.POOL)
        return calls

    def test_fills_every_slot_with_a_constructed_link(self):
        objects = [0x2100, 0x2200, 0x2300]
        mem = self.make_memory(objects)
        calls = self.refill(mem, 3, list(objects))
        self.assertEqual(calls['prepare'], [(self.GUARD, 3)])
        self.assertEqual(calls['take'], [self.POOL] * 3)
        self.assertEqual(calls['leave'], [self.GUARD])
        self.assertEqual(struct.unpack_from('<3Q', mem.regions[self.ELEMENTS]), tuple(objects))
        for index, link in enumerate(objects):
            self.assertEqual(mem.q(link), LINK_VTABLE)
            self.assertEqual(mem.q(link + 0x58), link + 0x68)
            self.assertEqual(mem.d(link + 0x40), 100 + index)
            self.assertEqual(mem.d(link + 0x60), 0)
            self.assertEqual(mem.d(link + 0x64), 1)
            self.assertEqual(mem.d(link + 0x80), 0xFFFFFFFF)
            self.assertEqual(mem.q(link + 0x78), 0)

    def test_construction_clears_stale_fields_and_sets_flag_bits(self):
        link = 0x2100
        mem = self.make_memory([link])
        mem.set_b(link + 0x84, 0xFF)
        mem.set_q(link + 0x8, 0x1234)
        self.refill(mem, 1, [link])
        self.assertEqual(mem.b(link + 0x84), 0xFD)  # bit1 cleared, bit0 set, others kept
        self.assertEqual(mem.q(link + 0x8), 0)
        self.assertEqual(mem.q(link + 0x20), 0)
        self.assertEqual(mem.q(link + 0x50), 0)

    def test_null_take_stores_null_and_constructs_nothing(self):
        mem = self.make_memory([0x2100, 0x2300])
        before = bytes(mem.regions[0x2100])
        calls = self.refill(mem, 3, [0x2100, 0, 0x2300])
        self.assertEqual(struct.unpack_from('<3Q', mem.regions[self.ELEMENTS]), (0x2100, 0, 0x2300))
        self.assertEqual(calls['serial'], [100, 101])  # no serial drawn for the null slot
        self.assertEqual(mem.q(0x2100), LINK_VTABLE)
        self.assertNotEqual(bytes(mem.regions[0x2100]), before)

    def test_zero_count_prepares_and_returns_without_takes(self):
        mem = self.make_memory([])
        calls = self.refill(mem, 0, [])
        self.assertEqual(calls['prepare'], [(self.GUARD, 0)])
        self.assertEqual(calls['take'], [])
        self.assertEqual(calls['serial'], [])
        self.assertEqual(calls['leave'], [self.GUARD])
        self.assertEqual(struct.unpack_from('<Q', mem.regions[self.ELEMENTS]), (0,))

    def test_composes_with_recycled_link_acquire(self):
        objects = [0x2100, 0x2200, 0x2300, 0x2400, 0x2500]
        vector = 0x3000
        mem = self.make_memory(objects)
        mem.add(vector, bytearray(0x10))
        mem.set_q(vector, self.ELEMENTS)
        mem.set_d(vector + 0xC, 8)
        serials = iter(range(40, 60))

        def refill(address, count):
            refill_pose_link_objects(mem, address, count, prepare=lambda g, n: None,
                                     take=lambda pool: objects.pop(0),
                                     leave_guard=lambda g: None,
                                     next_serial=lambda: next(serials),
                                     guard=self.GUARD, pool=self.POOL)

        link = acquire_pose_link(mem, vector, allocator=None, destroy=lambda p: None,
                                 refill=refill, next_serial=lambda: next(serials))
        self.assertEqual(link, 0x2500)
        self.assertEqual(mem.d(vector + 8), 4)
        self.assertEqual(mem.d(link + 0x80), 0xFFFFFFFF)
        self.assertEqual(mem.q(link), LINK_VTABLE)


if __name__ == '__main__':
    unittest.main()
