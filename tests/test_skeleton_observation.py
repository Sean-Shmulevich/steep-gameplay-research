import struct
import unittest
from engine.skeleton_observation import capture_skeleton_binding


class SkeletonObservationTests(unittest.TestCase):
    def setUp(self):
        self.memory = bytearray(0x20000)
        self.base = 0x100000
        self.entity = self.base + 0x1000
        self.component = self.base + 0x4000
        self.profile = dict(entity_tables=[0x200], skeleton_table=0x300,
                            type_getter=0x500, descriptor_global=0x600)
        self.put(self.entity, '<Q', self.base + 0x200)
        self.put(self.entity + 0x88, '<QHH', self.base + 0x3000, 0xbeef, 1)
        self.put(self.base + 0x3000, '<Q', self.component)
        self.put(self.entity + 0x1aa, '<BBH', 7, 99, 0)
        self.put(self.entity + 0x1f9, '<B', 7)
        self.put(self.component, '<Q', self.base + 0x300)
        self.put(self.component + 0x10, '<Q', self.entity)
        self.put(self.component + 0x258, '<Q', self.base + 0x7000)
        self.put(self.base + 0x330, '<Q', self.base + 0x500)
        self.write(self.base + 0x500, b'\x48\x8b\x05' + struct.pack('<i', 0xf9) + b'\xc3')
        self.put(self.base + 0x600, '<Q', self.base + 0x8000)
        self.put(self.base + 0x8018, '<Q', self.base + 0x9000)
        self.put(self.base + 0x804c, '<HH', 12, 19)
        self.write(self.base + 0x9000, b'SkeletonComponent\0')
        self.guard = (self.base + 0xa000, b'identity')
        self.write(*self.guard)

    def write(self, address, data):
        offset = address - self.base
        self.memory[offset:offset + len(data)] = data

    def put(self, address, fmt, *values):
        self.write(address, struct.pack(fmt, *values))

    def read(self, plan):
        self.assertLessEqual(len(plan), 32)
        return [bytes(self.memory[a-self.base:a-self.base+n]) for a, n in plan]

    def capture(self, read=None):
        return capture_skeleton_binding(read or self.read, self.entity, self.base,
                                        [self.guard], self.profile)

    def test_binding(self):
        result = self.capture()
        self.assertEqual(result['binding_status'], 'unique_exact_type')
        self.assertEqual(result['type_range'], [12, 19])
        self.assertTrue(result['owner_backlink_matches'])
        self.assertTrue(result['provider_bank_present'])
        self.assertFalse(result['cache_refresh_required'])
        self.assertFalse(result['atomic_snapshot'])
        self.assertFalse(result['lifetime_pinned'])
        self.assertNotIn(self.component, result.values())

    def test_identity_only_skips_mutable_bank(self):
        requests = []
        def tracked(plan):
            requests.extend(plan)
            return self.read(plan)
        result = capture_skeleton_binding(tracked, self.entity, self.base, [self.guard],
                                          self.profile, include_provider_bank=False)
        self.assertFalse(result['provider_bank_observed'])
        self.assertIsNone(result['provider_bank_present'])
        self.assertNotIn((self.component + 0x258, 8), requests)

    def test_stale_cache(self):
        for tag, index in [(8, 0), (7, 65534)]:
            self.put(self.entity + 0x1aa, '<BBH', tag, 0, index)
            self.assertTrue(self.capture()['cache_refresh_required'])
        self.put(self.entity + 0x1aa, '<BBH', 7, 0, 65535)
        self.assertFalse(self.capture()['cache_refresh_required'])

    def test_missing_and_ambiguous(self):
        self.put(self.entity + 0x92, '<H', 0)
        self.assertEqual(self.capture()['binding_status'], 'missing_exact_type')
        self.put(self.entity + 0x92, '<H', 2)
        self.put(self.base + 0x3008, '<Q', self.component)
        self.assertEqual(self.capture()['binding_status'], 'ambiguous_exact_type')

    def test_owner_is_observation(self):
        self.put(self.component + 0x10, '<Q', 0)
        self.assertFalse(self.capture()['owner_backlink_matches'])

    def test_bank_not_dereferenced(self):
        self.put(self.component + 0x258, '<Q', 1)
        self.assertTrue(self.capture()['provider_bank_present'])

    def test_maximum_count_batched(self):
        self.put(self.entity + 0x92, '<H', 256)
        self.write(self.base + 0x3000, struct.pack('<256Q', *([self.component] * 256)))
        result = self.capture()
        self.assertEqual(len(result['exact_type_indices']), 256)
        self.assertEqual(result['binding_status'], 'ambiguous_exact_type')

    def test_count_bound(self):
        self.put(self.entity + 0x92, '<H', 257)
        with self.assertRaisesRegex(ValueError, 'bound'):
            self.capture()

    def test_short_read(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.capture(lambda plan: [b'' for _ in plan])

    def test_type_validation(self):
        for address in [self.base + 0x330, self.base + 0x500, self.base + 0x9000]:
            with self.subTest(address=address):
                old = self.read([(address, 1)])[0]
                self.write(address, b'!')
                with self.assertRaises(ValueError):
                    self.capture()
                self.write(address, old)

    def test_changed_identity_spans(self):
        for target in [self.guard[0], self.entity + 0x88, self.entity + 0x1f9,
                       self.entity + 0x1aa, self.base + 0x3000, self.component,
                       self.component + 0x10, self.component + 0x258,
                       self.base + 0x804c]:
            with self.subTest(target=target):
                seen = 0
                def changing(plan):
                    nonlocal seen
                    result = self.read(plan)
                    for i, (address, _) in enumerate(plan):
                        if address == target:
                            seen += 1
                            if seen == 2:
                                result[i] = bytes([result[i][0] ^ 1]) + result[i][1:]
                    return result
                with self.assertRaisesRegex(ValueError, 'changed'):
                    self.capture(changing)

    def test_profile_validation(self):
        self.profile['type_getter'] = -1
        with self.assertRaisesRegex(ValueError, 'RVA'):
            self.capture()


if __name__ == '__main__':
    unittest.main()
