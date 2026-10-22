import json
from pathlib import Path
import unittest
from reference.transform_accessor_unlink import unlink_child,unlink_and_plan_cleanup,descriptor_is_valid,plan_descriptor_detach


class AccessorUnlinkTests(unittest.TestCase):
    def test_original_unlink_cleanup_chain(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/accessor_unlink_cleanup_validation.json').read_text())
        for sample in receipt['samples']:
            args=dict(sample['inputs']);args['next_links']={int(k):v for k,v in args['next_links'].items()}
            result=unlink_and_plan_cleanup(**args)
            self.assertEqual(json.loads(json.dumps(result)),sample['result'])

    def test_nonmember_link_cleared_without_removing_parent_child(self):
        links={'a':None,'other':'external'}
        result=unlink_child('a',links,'other')
        self.assertFalse(result['removed'])
        self.assertEqual(result['head'],'a')
        self.assertIsNone(result['next_links']['other'])
        self.assertEqual(links['other'],'external')

    def test_last_child_removal_changes_cleanup_gate(self):
        result=unlink_and_plan_cleanup(accessor_present=True,head='a',next_links={'a':None},
            child='a',descriptor_valid=False,sibling_present=False)
        self.assertTrue(result['cleanup']['owner_slot_cleared'])
        self.assertIsNone(result['head'])

    def test_inspector_rejects_nonterminating_walk(self):
        with self.assertRaisesRegex(ValueError,'cyclic'):
            unlink_child('a',{'a':'b','b':'a','missing':None},'missing')

    def test_original_descriptor_tls_cleanup_chain(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/accessor_descriptor_cleanup_validation.json').read_text())
        self.assertEqual(receipt['cases'],320)
        for sample in receipt['samples']:
            with self.subTest(descriptor=sample['descriptor'],reader=sample['reader_word']):
                args=dict(sample['inputs'])
                self.assertEqual(descriptor_is_valid(**sample['descriptor']),args['descriptor_valid'])
                args['next_links']={int(k):v for k,v in args['next_links'].items()}
                result=unlink_and_plan_cleanup(**args)
                self.assertEqual(json.loads(json.dumps(result)),sample['result'])

    def test_visibility_mask_requires_bit_intersection(self):
        args=dict(mode=1,first_target=0x100,first_status=0,second_target=0x200,
                  second_status=0,index=0,tls_mask=0x80)
        self.assertFalse(descriptor_is_valid(**args))
        self.assertTrue(descriptor_is_valid(**dict(args,tls_mask=0x100)))
        self.assertFalse(descriptor_is_valid(**dict(args,mode=2,tls_mask=0x100)))
        self.assertTrue(descriptor_is_valid(**dict(args,mode=2,tls_mask=0x200)))
        self.assertTrue(descriptor_is_valid(**dict(args,first_status=0x80000000)))
        self.assertFalse(descriptor_is_valid(**dict(args,first_status=0x80000000,first_target=0)))

    def test_index_sentinel_applies_only_to_second_mode(self):
        args=dict(mode=1,first_target=1,first_status=0x80000000,second_target=1,
                  second_status=0x80000000,index=65535,tls_mask=0)
        self.assertTrue(descriptor_is_valid(**args))
        for mode in (0,2,3,0xffffffff):
            self.assertFalse(descriptor_is_valid(**dict(args,mode=mode)))

    def test_original_descriptor_detach_dispatch(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/descriptor_detach_validation.json').read_text())
        self.assertEqual(receipt['cases'],128)
        for sample in receipt['samples']:
            with self.subTest(inputs=sample['inputs']):
                self.assertEqual(plan_descriptor_detach(**sample['inputs']),sample['result'])

    def test_dispatch_is_not_a_validity_or_pointer_safety_gate(self):
        args=dict(mode=2,first_target=0,first_status=0,second_target=0x300,
                  second_status=0,index=65535,tls_mask=0x100)
        self.assertFalse(descriptor_is_valid(**args))
        self.assertEqual(plan_descriptor_detach(**args),dict(service='indexed_detach',
            masked_target=0x100,index_forwarded=65535))
        args.update(mode=1,tls_mask=0)
        self.assertEqual(plan_descriptor_detach(**args),dict(service='direct_cleanup',
            masked_target=0,index_forwarded=None))
