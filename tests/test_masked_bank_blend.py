import json
from pathlib import Path
import unittest
from reference.animation_bank_blend import blend_masked_pose_bank


class MaskedBankTests(unittest.TestCase):
    def test_original_instruction_outputs(self):
        r=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/masked_bank_blend_validation.json').read_text())
        self.assertEqual(r['cases'],80)
        for row in r['rows']:
            def bank(data,vector):return dict(data=bytearray(data),profile=r['profile'],flags=0,
                records=[dict(id=7,vector=vector,rotation=[0,0,0,1])])
            dst=bank([0xcd]*64,[-1]*4);a=bank(r['first'],[1,2,3,4]);b=bank(r['second'],[5,6,7,8]);masks=[]
            visits=blend_masked_pose_bank(dst,a,b,row['weight'],0,row['mask'],
                weight_mode=row['mode'],uniform_groups=row['uniform_groups'],exclusion_mask=row['exclusion_mask'],
                reciprocal_sqrt=lambda n:self.fail('identity needs no seed'))
            self.assertEqual(list(dst['data']),row['output']);self.assertEqual(dst['flags'],row['flags'])
            self.assertEqual(dst['records'],row['records']);self.assertEqual(visits,row['visits'])

    def test_full_mask_ignores_uniform_override_and_keeps_copy_flag_clear(self):
        profile=dict(group_count=1,channel_count=1,group_words=[0,1,1,1,1,1,1],
            descriptors=[dict(key=1,kind=1,offset=0)])
        def bank(data):return dict(profile=profile,data=bytearray(data),flags=0,records=[])
        a,b=bank(b'aaaa'),bank(b'bbbb')
        dst=bank(b'cccc')
        blend_masked_pose_bank(dst,a,b,.3,0,65535,uniform_groups=1)
        self.assertEqual(dst['data'],b'bbbb');self.assertEqual(dst['flags'],0)
