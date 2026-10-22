import json
from pathlib import Path
import unittest
from reference.animation_bank_copy import copy_masked_pose_bank


class MaskedCopyTests(unittest.TestCase):
    def test_instruction_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/masked_copy_validation.json').read_text())
        self.assertEqual(receipt['cases'],128)
        for row in receipt['rows']:
            dst=dict(flags=row['flags'],parent_header=bytes(row['destination_header']),data=bytearray(row['destination_data']),group_words=row['group_words'],descriptors=row['descriptors'])
            src=dict(group_count=row['group_count'],parent_header=bytes(row['source_header']),data=bytes(row['source_data']))
            result=copy_masked_pose_bank(dst,src,row['mode'],row['request_mask'])
            self.assertEqual(result,row['visits']);self.assertEqual(list(dst['data']),row['expected_data'])
            self.assertEqual(list(dst['parent_header']),row['expected_header']);self.assertEqual(dst['flags'],row['expected_flags'])

    def test_full_mask_is_explicit_gap(self):
        with self.assertRaisesRegex(ValueError,'full-mask'):
            copy_masked_pose_bank({}, {},0,65535)

    def test_zero_mask_still_sets_ready_and_copies_header_when_allowed(self):
        dst=dict(flags=0,parent_header=bytes(32),data=bytearray(b'unchanged'),group_words=[],descriptors=[])
        src=dict(group_count=0,parent_header=bytes([7])*32,data=b'')
        self.assertEqual(copy_masked_pose_bank(dst,src,0,0),[])
        self.assertEqual(dst['flags'],1<<27);self.assertEqual(dst['parent_header'],src['parent_header'])
        self.assertEqual(dst['data'],b'unchanged')

    def test_full_copy_instruction_receipt(self):
        from reference.animation_bank_copy import copy_pose_bank
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/full_bank_copy_validation.json').read_text())
        self.assertEqual(receipt['cases'],192)
        for row in receipt['rows']:
            dst=dict(flags=row['flags'],parent_header=bytes(row['destination_header']),data=bytearray(row['destination_data']))
            src=dict(parent_header=bytes(row['source_header']),data=bytes(row['source_data']),bulk_boundaries=row['boundaries'])
            self.assertEqual(copy_pose_bank(dst,src,7,65535),row['result'])
            self.assertEqual(list(dst['data']),row['expected_data'])
            self.assertEqual(list(dst['parent_header']),row['expected_header']);self.assertEqual(dst['flags'],row['expected_flags'])

    def test_full_copy_refuses_unaligned_regions(self):
        from reference.animation_bank_copy import copy_pose_bank
        for boundaries in ([1,4,8],[32,33,40],[32,16,40]):
            dst=dict(flags=0,parent_header=bytes(32),data=bytearray(64))
            src=dict(parent_header=bytes(32),data=bytes(64),bulk_boundaries=boundaries)
            with self.assertRaises(ValueError):copy_pose_bank(dst,src,0,65535)
            self.assertEqual(dst['flags'],0)

    def test_attached_profile_overrides_stale_flat_metadata(self):
        from reference.animation_bank_copy import copy_pose_bank
        profile=dict(group_count=1,group_words=[0,1,1,1,1,1,1,1,1],descriptors=[dict(offset=4,kind=1)],bulk_boundaries=[0,8,8])
        dst=dict(flags=1<<26,parent_header=bytes(32),data=bytearray(16),profile=profile,group_words=[],descriptors=[])
        src=dict(parent_header=bytes(32),data=bytes(range(16)),profile=profile,group_count=0,bulk_boundaries=[0,0,0])
        copy_pose_bank(dst,src,0,1)
        self.assertEqual(dst['data'],bytes(4)+bytes(range(4,8))+bytes(8))
        profile['descriptors'][0]['offset']=8
        copy_pose_bank(dst,src,0,1)
        self.assertEqual(dst['data'][8:12],bytes(range(8,12)))
        copy_pose_bank(dst,src,0,65535)
        self.assertEqual(dst['data'][:8],bytes(range(8)))
