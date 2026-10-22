import json
import unittest
from pathlib import Path
from reference.animation_channels import copy_typed_channels


class TypedChannelCopyTests(unittest.TestCase):
    def test_native_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
                              'native/snow_host/typed_channel_copy_validation.json').read_text())
        kinds = set()
        for row in receipt['rows']:
            args = dict(row['inputs'])
            args['storage'] = bytes.fromhex(args['storage'])
            got = copy_typed_channels(**args)
            self.assertEqual(got['storage'].hex(), row['storage'])
            self.assertEqual(got['flags'], row['flags'])
            kinds.update(word & 15 for _, word in args['entries'][args['first']:args['first']+args['count']])
        self.assertEqual(kinds, set(range(16)))

    def test_ordered_overlap(self):
        data = bytes(range(32))
        result = copy_typed_channels(data, 0, 4, [(0, 4)], 0, 1, 0)
        self.assertEqual(result['storage'][4:16], data[:4] * 3)
        self.assertEqual(data, bytes(range(32)))

    def test_empty_sets_flag(self):
        result = copy_typed_channels(b'', 0, 0, [], 0, 0, 0x123)
        self.assertEqual(result['flags'], 0x08000123)
        self.assertEqual(result['storage'], b'')

    def test_descriptor_order(self):
        result = copy_typed_channels(bytes(range(16)), 0, 4, [(0, 1), (4, 1)], 0, 2, 0)
        self.assertEqual(result['storage'][4:12], bytes(range(4))*2)

    def test_storage_and_range_bounds(self):
        with self.assertRaisesRegex(ValueError, 'storage'):
            copy_typed_channels(bytes(16), 0, 8, [(0, 4)], 0, 1, 0)
        with self.assertRaisesRegex(ValueError, 'descriptor range'):
            copy_typed_channels(bytes(16), 0, 0, [], 0, 1, 0)

    def test_aligned_vector_policy(self):
        with self.assertRaisesRegex(ValueError, 'aligned'):
            copy_typed_channels(bytes(32), 0, 4, [(0, 5)], 0, 1, 0)

    def test_high_type_bits_ignored(self):
        self.assertEqual(copy_typed_channels(bytes(range(32)), 0, 16, [(0, 0xfff0)], 0, 1, 0)['storage'][16:20],
                         bytes([0, 17, 18, 19]))


class ChannelCopyRouteTests(unittest.TestCase):
    def route(self, **changes):
        from reference.animation_channels import select_channel_copy
        args = dict(mode=1, weight=0.5, group_mask=65535, selector=0,
                    total_count=9, groups=[[i, 1, 2, 3, 4, 5, 6] for i in range(3)])
        args.update(changes)
        return select_channel_copy(**args)

    def test_native_route_receipt(self):
        from reference.animation_channels import select_channel_copy
        receipt = json.loads((Path(__file__).resolve().parents[1] /
                              'native/snow_host/channel_copy_route_validation.json').read_text())
        for row in receipt['rows']:
            self.assertEqual(select_channel_copy(**row['inputs']), row['route'])

    def test_half_threshold(self):
        self.assertEqual(self.route(weight=0.49999997)['source'], 'first')
        self.assertEqual(self.route(weight=0.5)['source'], 'second')
        self.assertEqual(self.route(weight=0.50000006)['source'], 'second')

    def test_forced_modes(self):
        self.assertEqual(self.route(mode=2, weight=10)['source'], 'first')
        self.assertEqual(self.route(mode=3, weight=-10)['source'], 'second')

    def test_highest_bit_group(self):
        self.assertEqual(self.route(group_mask=3)['group_index'], 1)
        self.assertEqual(self.route(group_mask=0)['group_index'], 0)
        self.assertEqual(self.route(group_mask=7, selector=2)['count'], 3)

    def test_entire_table_ignores_group_selector(self):
        self.assertEqual(self.route(selector=100, groups=[])['count'], 9)

    def test_unsupported_modes_and_ranges(self):
        with self.assertRaisesRegex(ValueError, 'copy mode'):
            self.route(mode=4)
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            self.route(group_mask=1, total_count=0)
        with self.assertRaisesRegex(ValueError, 'six'):
            self.route(group_mask=1, selector=6)


if __name__ == '__main__':
    unittest.main()
