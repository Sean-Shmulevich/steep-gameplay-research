import struct
import unittest
from engine.pose_link_state_reset import reset_pose_link_state


def make_link(entries, held, array=0x5000):
    link = bytearray(b'\xaa' * 0x90)
    struct.pack_into('<QQ', link, 8, 0x111, 0x222)
    struct.pack_into('<QI', link, 0x58, array, len(entries))
    struct.pack_into('<Q', link, 0x78, held)
    raw = b''.join(struct.pack('<QQ', k, p) for k, p in entries)
    return link, {array: bytearray(raw)}


class LinkStateResetTests(unittest.TestCase):
    def run_reset(self, link, arrays):
        events = []
        reset_pose_link_state(
            link, entry_arrays=arrays,
            release_contact=lambda t: events.append(('contact', t, bytes(link[8:0x18]), bytes(link[0x78:0x80]))),
            release_held=lambda t: events.append(('held', t, bytes(link[8:0x18]), struct.unpack_from('<I', link, 0x60)[0])))
        return events

    def test_order_and_state_seen_by_services(self):
        link, arrays = make_link([(1, 10), (2, 0), (3, 30)], 77)
        events = self.run_reset(link, arrays)
        self.assertEqual([e[:2] for e in events], [('contact', 10), ('contact', 30), ('held', 77)])
        self.assertEqual(events[0][2], bytes(16))
        self.assertEqual(events[0][3], struct.pack('<Q', 77))  # held not yet cleared
        self.assertEqual(events[2][3], 0)  # contact count already cleared when held is returned
        self.assertEqual(struct.unpack_from('<QQ', link, 8), (0, 0))
        self.assertEqual(struct.unpack_from('<Q', link, 0x78)[0], 0)
        self.assertEqual(struct.unpack_from('<I', link, 0x60)[0], 0)

    def test_null_held_and_empty_contacts_call_nothing_and_touch_only_fields(self):
        link, arrays = make_link([], 0)
        before = bytes(link)
        self.assertEqual(self.run_reset(link, {}), [])
        expected = bytearray(before)
        expected[8:0x18] = bytes(16)
        self.assertEqual(bytes(link), bytes(expected))

    def test_ring_links_entries_and_capacity_persist(self):
        link, arrays = make_link([(5, 50)], 9)
        link[0x20:0x40] = bytes(range(32))
        link[0x64:0x68] = b'\x07\0\0\0'
        before = bytes(link)
        entries = bytes(arrays[0x5000])
        self.run_reset(link, arrays)
        self.assertEqual(link[0x20:0x58], before[0x20:0x58])
        self.assertEqual(link[0x64:0x78], before[0x64:0x78])
        self.assertEqual(link[0x80:], before[0x80:])
        self.assertEqual(bytes(arrays[0x5000]), entries)
        self.assertEqual(struct.unpack_from('<I', link, 0x60)[0], 0)

    def test_service_failure_leaves_held_payload_in_place(self):
        link, arrays = make_link([], 5)

        def boom(token):
            raise RuntimeError

        with self.assertRaises(RuntimeError):
            reset_pose_link_state(link, entry_arrays=arrays, release_contact=None, release_held=boom)
        self.assertEqual(struct.unpack_from('<Q', link, 0x78)[0], 5)
        self.assertEqual(struct.unpack_from('<QQ', link, 8), (0, 0))


if __name__ == '__main__':
    unittest.main()
