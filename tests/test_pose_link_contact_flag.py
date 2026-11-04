import unittest

from engine.pose_link_contact_flag import refresh_pose_link_contact_flag
from engine.pose_pair_link_worker import PoseFlatMemory


class PoseLinkContactFlagTests(unittest.TestCase):
    LINK = 0x1000

    def make_link(self, flags, payloads):
        """payloads: list of payload flag bytes (None means no payload object is mapped)."""
        link = bytearray(0x100)
        link[0x84] = flags
        regions = {self.LINK: link}
        for index, value in enumerate(payloads):
            address = 0x4000 + 0x200 * index
            obj = bytearray(0x200)
            obj[0x114] = value
            regions[address] = obj
        mem = PoseFlatMemory(regions)
        return mem, [0x4000 + 0x200 * i for i in range(len(payloads))]

    def refresh(self, mem, addresses):
        seen = []
        container_value = self.LINK + 0x48

        def contact_count(container):
            seen.append(('count', container))
            return len(addresses)

        def contact_payload(container, index):
            seen.append(('payload', container, index))
            return addresses[index]

        found = refresh_pose_link_contact_flag(mem, self.LINK, contact_count=contact_count,
                                               contact_payload=contact_payload)
        self.assertEqual(seen[0], ('count', container_value))
        return found, seen

    def test_flagged_payload_sets_bit0_and_keeps_other_bits(self):
        mem, addresses = self.make_link(0x12, [0, 1, 0])
        found, _ = self.refresh(mem, addresses)
        self.assertTrue(found)
        self.assertEqual(mem.b(self.LINK + 0x84), 0x13)

    def test_no_flagged_payload_clears_bit0_and_keeps_other_bits(self):
        mem, addresses = self.make_link(0xFF, [0, 2, 0x10])
        found, _ = self.refresh(mem, addresses)
        self.assertFalse(found)
        self.assertEqual(mem.b(self.LINK + 0x84), 0xFE)

    def test_only_bit0_of_the_payload_counts(self):
        mem, addresses = self.make_link(0x01, [2, 0xFE, 0x80])
        found, _ = self.refresh(mem, addresses)
        self.assertFalse(found)
        self.assertEqual(mem.b(self.LINK + 0x84), 0x00)

    def test_scan_stops_at_first_flagged_payload(self):
        mem, addresses = self.make_link(0x00, [0, 1, 1])
        found, seen = self.refresh(mem, addresses)
        self.assertTrue(found)
        self.assertEqual([c for c in seen if c[0] == 'payload'],
                         [('payload', self.LINK + 0x48, 0), ('payload', self.LINK + 0x48, 1)])

    def test_flag_on_last_payload_is_found(self):
        mem, addresses = self.make_link(0x00, [0, 0, 0, 1])
        found, seen = self.refresh(mem, addresses)
        self.assertTrue(found)
        self.assertEqual(len([c for c in seen if c[0] == 'payload']), 4)

    def test_empty_contact_span_clears_the_flag(self):
        mem, _ = self.make_link(0x01, [])
        found, seen = self.refresh(mem, [])
        self.assertFalse(found)
        self.assertEqual(mem.b(self.LINK + 0x84), 0x00)
        self.assertEqual(len(seen), 1)

    def test_null_payload_faults_like_the_native_read(self):
        mem, _ = self.make_link(0x00, [])
        with self.assertRaises(KeyError):
            refresh_pose_link_contact_flag(mem, self.LINK,
                                           contact_count=lambda c: 1,
                                           contact_payload=lambda c, i: 0)
        self.assertEqual(mem.b(self.LINK + 0x84), 0x00)


if __name__ == '__main__':
    unittest.main()
