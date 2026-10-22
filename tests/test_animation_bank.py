import json
import unittest
from pathlib import Path
from reference.animation_bank import advance_pose_bank


class PoseBankRotationTests(unittest.TestCase):
    def args(self, **changes):
        args = dict(current=0, previous=1, stored_epoch=1, epoch=2,
                    bank_flags=[0, 0], component_flags=0,
                    owner_publication_present=True, published_bank=0, publication_flags=0)
        args.update(changes)
        return args

    def test_native_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
                              'native/snow_host/pose_bank_rotation_validation.json').read_text())
        for row in receipt['rows']:
            self.assertEqual(advance_pose_bank(**row['inputs']), row['result'])

    def test_epoch_idempotence_and_next_rotation(self):
        args = self.args()
        first = advance_pose_bank(**args)
        self.assertEqual((first['current'], first['previous']), (1, 0))
        args.update({k:v for k,v in first.items() if k != 'rotated'})
        second = advance_pose_bank(**args)
        self.assertFalse(second['rotated'])
        self.assertEqual(second['bank_flags'], first['bank_flags'])
        args['epoch'] = 3
        third = advance_pose_bank(**args)
        self.assertEqual((third['current'], third['previous']), (0, 1))

    def test_initial_without_publication_skips_rotation(self):
        result = advance_pose_bank(**self.args(stored_epoch=0xffffffff,
                                              owner_publication_present=False, component_flags=8))
        self.assertFalse(result['rotated'])
        self.assertEqual(result['current'], 0)
        self.assertEqual(result['previous'], 0)
        self.assertEqual(result['stored_epoch'], 2)
        self.assertEqual(result['bank_flags'][0], 1 << 31)

    def test_equal_epoch_changes_nothing(self):
        result = advance_pose_bank(**self.args(stored_epoch=2, component_flags=0x38))
        self.assertFalse(result['rotated'])
        self.assertEqual(result['bank_flags'], [0, 0])
        self.assertEqual(result['publication_flags'], 0)

    def test_external_current_selects_first(self):
        result = advance_pose_bank(**self.args(current=2, bank_flags=[0,0,123]))
        self.assertEqual(result['current'], 0)
        self.assertEqual(result['previous'], 2)
        self.assertEqual(result['bank_flags'][2], 123)

    def test_flag_preservation_and_publication(self):
        result = advance_pose_bank(**self.args(bank_flags=[0x55, 0xffffffff], publication_flags=0x10))
        self.assertEqual(result['bank_flags'], [0x20000055, 0x5fffffff])
        self.assertEqual(result['publication_flags'], 0x18)
        self.assertEqual(result['published_bank'], 1)

    def test_input_not_mutated(self):
        args = self.args();advance_pose_bank(**args)
        self.assertEqual(args['bank_flags'], [0, 0])


class RotationAccessorTests(unittest.TestCase):
    def test_native_receipt(self):
        from reference.animation_bank import refresh_then_read_rotation
        receipt = json.loads((Path(__file__).resolve().parents[1] /
                              'native/snow_host/rotation_accessor_validation.json').read_text())
        for row in receipt['rows']:
            bank = [0]
            events = []
            def refresh(force, secondary):
                self.assertEqual((force, secondary), (False, False))
                events.append('refresh')
                bank[0] = 1
            def read(selected, index):
                self.assertEqual(index, row['channel_index'])
                return row['bank_rotations'][selected]
            result = refresh_then_read_rotation(row['dirty_byte'], row['channel_index'],
                                                refresh, lambda: bank[0], read)
            self.assertEqual(result, row['result'])
            self.assertEqual(events, row['events'])

    def test_refresh_failure_prevents_read(self):
        from reference.animation_bank import refresh_then_read_rotation
        events = []
        def fail(*args):
            raise RuntimeError('refresh failed')
        with self.assertRaisesRegex(RuntimeError, 'refresh failed'):
            refresh_then_read_rotation(128, 0, fail, lambda: events.append('select'),
                                       lambda *_: events.append('read'))
        self.assertEqual(events, [])

    def test_missing_index_policy_belongs_to_reader(self):
        from reference.animation_bank import refresh_then_read_rotation
        def read(bank, index):
            if index == 65535:
                raise ValueError('missing channel')
        with self.assertRaisesRegex(ValueError, 'missing channel'):
            refresh_then_read_rotation(0, 65535, lambda *_: None, lambda: 0, read)


if __name__ == '__main__':
    unittest.main()
