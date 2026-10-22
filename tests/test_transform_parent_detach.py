import json
from pathlib import Path
import unittest
from reference.transform_parent_detach import plan_parent_detach


class ParentDetachTests(unittest.TestCase):
    def test_original_outer_detach_chain(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/parent_detach_validation.json').read_text())
        self.assertEqual(receipt['cases'],288)
        for sample in receipt['samples']:
            with self.subTest(inputs=sample['inputs']):
                self.assertEqual(plan_parent_detach(**sample['inputs']),sample['result'])

    def test_retained_holders_do_not_pin_accessors(self):
        args=dict(mode=1,visible=True,allow_free=True,sibling_present=False,
                  children_present=False,reader_word=3,initial_holder_count=4)
        result=plan_parent_detach(**args)
        frees=[event for event in result['events'] if event['event'].startswith('free_')]
        self.assertEqual([event['first_count'] for event in frees],[5,4])
        self.assertTrue(result['parent_accessor_freed'])
        self.assertTrue(result['child_accessor_freed'])
        self.assertEqual(result['final_holder_count'],3)
        self.assertEqual(plan_parent_detach(**dict(args,reader_word=0)),result)

    def test_no_free_request_still_detaches_parent(self):
        result=plan_parent_detach(mode=1,visible=True,allow_free=False,
            sibling_present=False,children_present=False,reader_word=0,initial_holder_count=2)
        self.assertTrue(result['parent_accessor_freed'])
        self.assertFalse(result['child_accessor_freed'])
        self.assertEqual(result['final_holder_count'],1)

    def test_rejects_unmodeled_mode_and_last_reference(self):
        args=dict(mode=1,visible=True,allow_free=True,sibling_present=False,
                  children_present=False,reader_word=0,initial_holder_count=4)
        for change in ({'mode':2},{'initial_holder_count':1}):
            with self.assertRaises(ValueError):plan_parent_detach(**dict(args,**change))
