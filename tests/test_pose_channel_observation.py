import struct
import json
from pathlib import Path
import unittest
from engine.pose_channel_observation import capture_pose_channels


class PoseChannelObservationTests(unittest.TestCase):
    def setUp(self):
        self.memory = bytearray(0x20000)
        self.base = 0x100000
        self.component = self.base + 0x1000
        self.requests = []
        self.put(self.component + 0x240, '<Q', self.base + 0x2000)
        self.put(self.base + 0x2038, '<QHH', self.base + 0x3000, 0xabcd, 3)
        self.put(self.base + 0x3000, '<6I', 10, 0xabcd0000, 10, 1, 20, 1)
        self.put(self.component + 0x258, '<Q', self.base + 0x4000)
        self.put(self.base + 0x4000, '<8f', 10, 20, 30, 0, 0, 0, 0, 1)
        self.put(self.base + 0x4190, '<Q', self.base + 0x7000)
        self.put(self.base + 0x7014, '<HH', 64, 32)
        self.put(self.base + 0x705a, '<H', 2)
        self.put(self.base + 0x4198, '<Q', self.base + 0x5000)
        self.put(self.base + 0x5000, '<16f', 1, 2, 3, 0, 0, 0, 0, 1,
                 4, 5, 6, 0, 0, 0, 0, 1)
        self.guard = (self.base + 0x6000, b'identity')
        self.write(*self.guard)

    def write(self, address, data):
        offset = address - self.base
        self.memory[offset:offset+len(data)] = data

    def put(self, address, fmt, *values):
        self.write(address, struct.pack(fmt, *values))

    def read(self, plan):
        self.assertLessEqual(len(plan), 32)
        self.assertTrue(all(n <= 4096 for _, n in plan))
        self.requests.extend(plan)
        return [bytes(self.memory[a-self.base:a-self.base+n]) for a, n in plan]

    def capture(self, keys=(10, 20, 30), count=2, read=None):
        return capture_pose_channels(read or self.read, self.component, keys, count, [self.guard])

    def test_metadata_bounds(self):
        result = self.capture(count=None)
        self.assertEqual(result['record_count'], 2)
        self.assertEqual(result['record_count_source'], 'native_metadata')
        self.assertTrue(result['bank_layout']['transforms_fit_allocation'])

    def test_metadata_allocation_mismatch(self):
        self.put(self.base + 0x408c, '<I', 1 << 28)
        with self.assertRaisesRegex(ValueError, 'allocation size'):
            self.capture(count=None)
        self.assertNotIn((self.base + 0x5000, 32), self.requests)

    def test_metadata_count_rejects_index(self):
        self.put(self.base + 0x705a, '<H', 1)
        with self.assertRaisesRegex(ValueError, 'metadata record count'):
            self.capture(count=None)

    def test_metadata_guard_changes(self):
        for target in [self.base + 0x4190, self.base + 0x7014, self.base + 0x705a]:
            seen = 0
            def changing(plan):
                nonlocal seen
                result = self.read(plan)
                for i, (a, _) in enumerate(plan):
                    if a == target:
                        seen += 1
                        if seen == 2:
                            result[i] = bytes([result[i][0] ^ 1]) + result[i][1:]
                return result
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.capture(count=None, read=changing)

    def test_metadata_missing_channel_no_bank(self):
        result = self.capture(count=None, keys=[99])
        self.assertIsNone(result['record_count'])
        self.assertEqual(result['record_count_source'], 'metadata_not_read')

    def test_native_metadata_receipt(self):
        from reference.ground_response_pose import pose_bank_layout
        path = Path(__file__).resolve().parents[1] / 'native/snow_host/pose_bank_layout_validation.json'
        for case in json.loads(path.read_text())['rows']:
            got = pose_bank_layout(**case['inputs'])
            self.assertEqual(got['transform_count'], case['native_count'])
            self.assertEqual(got['allocation_bytes'], case['native_allocation_bytes'])

    def test_local_and_converted(self):
        rows = self.capture()['channels']
        self.assertEqual([r['index'] for r in rows], [0, 1, 65535])
        self.assertEqual(rows[0]['inputs']['position'], [1, 2, 3, 0])
        self.assertEqual(rows[0]['converted']['position'], (11, 22, 33, 0))
        self.assertFalse(rows[2]['found'])

    def test_direct_flag(self):
        self.put(self.base + 0x408c, '<I', 1 << 26)
        self.assertEqual(self.capture()['channels'][0]['converted']['position'], (1, 2, 3, 0))

    def test_null_table_does_not_read_bank(self):
        self.put(self.component + 0x240, '<Q', 0)
        self.assertFalse(any(r['found'] for r in self.capture()['channels']))
        self.assertNotIn((self.component + 0x258, 8), self.requests)

    def test_missing_key_no_bank(self):
        self.capture(keys=[99])
        self.assertNotIn((self.component + 0x258, 8), self.requests)

    def test_bounds_before_record_read(self):
        with self.assertRaisesRegex(ValueError, 'record count'):
            self.capture(count=1)
        self.assertNotIn((self.base + 0x5000, 32), self.requests)

    def test_invalid_record_base(self):
        self.put(self.base + 0x4198, '<Q', 0)
        with self.assertRaises(ValueError):
            self.capture()

    def test_unsorted(self):
        self.put(self.base + 0x3000, '<I', 11)
        with self.assertRaisesRegex(ValueError, 'sorted'):
            self.capture()

    def test_large_table(self):
        self.put(self.base + 0x2042, '<H', 4097)
        with self.assertRaisesRegex(ValueError, 'bound'):
            self.capture()

    def test_nonfinite(self):
        self.put(self.base + 0x5000, '<f', float('nan'))
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            self.capture()

    def test_short_read(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.capture(read=lambda plan: [])

    def test_change_in_retained_spans(self):
        for target in [self.guard[0], self.component + 0x240, self.base + 0x2038,
                       self.base + 0x3000, self.component + 0x258, self.base + 0x4000,
                       self.base + 0x408c, self.base + 0x4198, self.base + 0x5000]:
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
                    self.capture(read=changing)

    def test_existing_native_transform_receipt(self):
        path = Path(__file__).resolve().parents[1] / 'native/snow_host/provider_pose_validation.json'
        for case in json.loads(path.read_text())['rows']:
            args = case['inputs']
            self.put(self.base + 0x4000, '<8f', *(args['parent_position'] + args['parent_rotation']))
            self.put(self.base + 0x5000, '<8f', *(args['position'] + args['rotation']))
            self.put(self.base + 0x408c, '<I', (1 << 26) if args['direct'] else 0)
            got = self.capture(keys=[10])['channels'][0]['converted']
            for field in ['position', 'rotation']:
                self.assertEqual(struct.pack('<4f', *got[field]),
                                 struct.pack('<4f', *case['result'][field]))

    def test_linked_object_conversion_receipt_through_existing_reader(self):
        path = Path(__file__).resolve().parents[1] / 'native/snow_host/skeleton_provider_pose_validation.json'
        receipt = json.loads(path.read_text())
        self.assertEqual(receipt['cases'], 120)
        for case in receipt['samples']:
            args = case['inputs']
            self.put(self.base + 0x4000, '<8f', *(args['base_position'] + args['base_rotation']))
            self.put(self.base + 0x5000, '<8f', *(args['position'] + args['rotation']))
            self.put(self.base + 0x408c, '<I', (1 << 26) if args['already_transformed'] else 0)
            got = self.capture(keys=[10])['channels'][0]['converted']
            self.assertEqual(struct.pack('<3f', *got['position'][:3]),
                             struct.pack('<3f', *case['result']['position']))
            self.assertEqual(struct.pack('<4f', *got['rotation']),
                             struct.pack('<4f', *case['result']['rotation']))

    def test_chunked_table(self):
        self.put(self.base + 0x2042, '<H', 4096)
        self.put(self.base + 0x2038, '<Q', self.base + 0x8000)
        self.write(self.base + 0x8000, b''.join(struct.pack('<II', i, 65535) for i in range(4096)))
        result = self.capture(keys=[3000])
        self.assertFalse(result['channels'][0]['found'])


if __name__ == '__main__':
    unittest.main()
