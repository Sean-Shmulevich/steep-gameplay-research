import json
from pathlib import Path
import unittest
from reference.animation_target_retirement import record_target_association


class TargetAssociationTests(unittest.TestCase):
    def test_original_service_paths(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/target_retirement_validation.json').read_text())
        for sample in receipt['samples']:
            self.assertEqual(record_target_association(**sample['inputs']),sample['result'])

    def test_overwrite_does_not_invent_cleanup_of_stale_reverse_entries(self):
        forward={'a':'old'};reverse={'old':'a','new':'b'}
        result=record_target_association(forward,reverse,target_key='a',
            backing_key='new',locked_target_word=1<<28)
        self.assertEqual(result['target_to_backing'],{'a':'new'})
        self.assertEqual(result['backing_to_target'],{'old':'a','new':'a'})
        self.assertEqual(forward,{'a':'old'})
        self.assertEqual(reverse,{'old':'a','new':'b'})

    def test_original_removal_gates(self):
        from reference.animation_target_retirement import remove_target_association
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/target_removal_validation.json').read_text())
        for sample in receipt['samples']:
            self.assertEqual(remove_target_association(**sample['inputs']),sample['result'])

    def test_clear_flag_can_leave_associations(self):
        from reference.animation_target_retirement import remove_target_association
        result=remove_target_association({'t':'b'},{'b':'t'},target_key='t',
            target_word=(1<<28)|1,enabled=True)
        self.assertEqual(result['target_word'],1)
        self.assertEqual(result['target_to_backing'],{'t':'b'})
        self.assertEqual(result['backing_to_target'],{'b':'t'})
        self.assertEqual(result['events'],[])
