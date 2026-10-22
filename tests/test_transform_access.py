import json
from pathlib import Path
import unittest
from reference.transform_access import plan_transform_access


class TransformAccessTests(unittest.TestCase):
    def test_original_instruction_cases(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/transform_access_validation.json').read_text())
        self.assertEqual(receipt['cases'], 60)
        for case in receipt['samples']:
            self.assertEqual(plan_transform_access(**case['inputs']), case['result'])
        self.assertEqual(receipt['sequential_reuse'], dict(calls=2,
                         same_return_storage=True, first_result_overwritten=True,
                         reader_count_after=0))

    def test_race_undo_preserves_competing_writer_word(self):
        result = plan_transform_access(0, False, False, 0x100003)
        self.assertEqual(result['outcome'], 'retry')
        self.assertEqual(result['count_after'], 0x100003)

    def test_owner_bypass_requires_both_predicates(self):
        self.assertEqual(plan_transform_access(0x100000, True, True)['outcome'], 'copy')
        self.assertEqual(plan_transform_access(0x100000, True, False)['outcome'], 'retry')
        self.assertEqual(plan_transform_access(0x100000, False, True)['outcome'], 'retry')

    def test_reader_increment_can_cross_into_busy_mask(self):
        result = plan_transform_access(0xfffff, False, False)
        self.assertEqual(result['outcome'], 'retry')
        self.assertEqual(result['count_after'], 0xfffff)


class TransformWriteTests(unittest.TestCase):
    def test_original_instruction_cases(self):
        from reference.transform_access import plan_transform_write
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/transform_write_validation.json').read_text())
        self.assertEqual(receipt['cases'], 192)
        for case in receipt['samples']:
            self.assertEqual(plan_transform_write(**case['inputs']), case['result'])

    def test_writer_claim_blocks_new_readers_while_waiting(self):
        from reference.transform_access import plan_transform_write
        writer = plan_transform_write(3, 0xffffffff, 7, False, 0, 31)
        self.assertEqual(writer['outcome'], 'wait_readers')
        self.assertEqual(writer['count_after'], 0x100003)
        reader = plan_transform_access(writer['count_after'], False, False)
        self.assertEqual(reader['outcome'], 'retry')

    def test_normal_publication_masks_flag_and_releases_claim(self):
        from reference.transform_access import plan_transform_write
        writer = plan_transform_write(0, 0xffffffff, 7, False, 0, 31)
        self.assertEqual(writer['publication'], dict(count=0x100000, owner=7,
                                                    depth=1, flags=29))
        self.assertEqual(writer['count_after'], 0)
        self.assertEqual(writer['owner_after'], 0xffffffff)

    def test_nested_owner_publication_retains_outer_claim(self):
        from reference.transform_access import plan_transform_write
        writer = plan_transform_write(0x100000, 7, 7, True, 2, 31)
        self.assertEqual(writer['publication']['depth'], 3)
        self.assertEqual(writer['depth_after'], 2)
        self.assertEqual(writer['count_after'], 0x100000)
        self.assertEqual(writer['owner_after'], 7)


class TransformCopyTests(unittest.TestCase):
    def test_copy_out_uses_same_admission_model(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/transform_copy_validation.json').read_text())
        self.assertEqual(receipt['cases'], 60)
        for case in receipt['samples']:
            self.assertEqual(plan_transform_access(**case['inputs']), case['result'])
        self.assertEqual(receipt['sequential_copy'], dict(calls=2,
                         distinct_destinations=True, first_result_preserved=True))

    def test_constructor_defaults_do_not_claim_active_writer(self):
        from reference.transform_access import initial_transform_access_state
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/transform_copy_validation.json').read_text())
        state = initial_transform_access_state()
        self.assertEqual(state, receipt['constructor'])
        reader = plan_transform_access(state['reader_word'], False,
                                       bool(state['owner_bypass_enabled']))
        self.assertEqual(reader['path'], 'reader')
        self.assertEqual(state['depth'], 0)


class AccessorCleanupTests(unittest.TestCase):
    def test_original_cleanup_cases(self):
        from reference.transform_access import plan_accessor_cleanup
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/accessor_cleanup_validation.json').read_text())
        self.assertEqual(receipt['cases'], 48)
        for case in receipt['samples']:
            self.assertEqual(plan_accessor_cleanup(**case['inputs']), case['result'])

    def test_each_post_unlink_dependency_prevents_free(self):
        from reference.transform_access import plan_accessor_cleanup
        for predicates in ((True, False, False), (False, True, False), (False, False, True)):
            result = plan_accessor_cleanup(True, *predicates)
            self.assertFalse(result['owner_slot_cleared'])
            self.assertEqual(result['calls'], ['unlink', 'descriptor_valid'])

    def test_empty_dependencies_release_then_free(self):
        from reference.transform_access import plan_accessor_cleanup
        result = plan_accessor_cleanup(True, False, False, False)
        self.assertTrue(result['owner_slot_cleared'])
        self.assertEqual(result['calls'][-3:], ['release_descriptor_second',
                         'release_descriptor_first', 'free_accessor'])


class TransformTeardownTests(unittest.TestCase):
    def test_original_teardown_order(self):
        from reference.transform_access import plan_transform_teardown
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/transform_teardown_validation.json').read_text())
        self.assertEqual(receipt['cases'], 16)
        for case in receipt['samples']:
            self.assertEqual(plan_transform_teardown(case['accessor_present'],
                             case['indexed'], case['alternate_invalidation']), case['calls'])
