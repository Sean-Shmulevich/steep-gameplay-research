import json
from pathlib import Path
import unittest
from reference.animation_bank_blend import blend_additive_pose_bank


class AdditiveBankTests(unittest.TestCase):
    def test_additive_instruction_receipt(self):
        import struct
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/additive_bank_blend_validation.json').read_text())
        self.assertEqual(receipt['cases'],180)
        for row in receipt['rows']:
            profile=receipt['profile'];rotation=row['rotation'];used=[]
            def seed(length):
                i=len(used);used.append(length)
                self.assertEqual(length,row['lengths'][i])
                return row['seeds'][i]
            def record(vector,rotation):return dict(id=7,vector=vector,rotation=rotation)
            dst=dict(data=bytearray([0xcd]*80),profile=profile,flags=0,
                     records=[record([-1]*4,[0,0,0,1])])
            a=dict(data=bytes(receipt['first']),profile=profile,
                   records=[record([1,2,3,4],[0,0,0,1])])
            b=dict(data=bytes([20]*64)+struct.pack('<4f',*rotation),profile=profile,
                   records=[record([5,6,7,8],rotation)])
            visits=blend_additive_pose_bank(dst,a,b,row['weight'],0,row['mask'],
                swap=row['swap'],exclusion_mask=row['exclusion_mask'],reciprocal_sqrt=seed)
            self.assertEqual(list(dst['data']),row['output'])
            self.assertEqual(dst['records'],row['records'])
            self.assertEqual(dst['flags'],row['flags'])
            self.assertEqual(visits,row['visits'])
            self.assertEqual(len(used),len(row['seeds']))


    def test_masked_additive_instruction_receipt(self):
        import struct
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/masked_additive_bank_validation.json').read_text())
        self.assertEqual(receipt['cases'],432)
        for row in receipt['rows']:
            profile=receipt['profile'];rotation=row['rotation'];used=[]
            def seed(length):
                i=len(used);used.append(length)
                self.assertEqual(length,row['lengths'][i])
                return row['seeds'][i]
            def record(vector,rotation):return dict(id=7,vector=vector,rotation=rotation)
            dst=dict(data=bytearray([0xcd]*96),profile=profile,flags=0,
                     records=[record([-1]*4,[0,0,0,1])])
            a=dict(data=bytes([10]*64)+struct.pack('<4f',0,0,0,1)+bytes([row['byte']])*16,profile=profile,
                   records=[record([1,2,3,4],[0,0,0,1])])
            b=dict(data=bytes([20]*64)+struct.pack('<4f',*rotation)+bytes([row['byte']])*16,profile=profile,
                   records=[record([5,6,7,8],rotation)])
            visits=blend_additive_pose_bank(dst,a,b,row['weight'],0,row['mask'],
                weight_mode=row['mode'],swap=row['swap'],exclusion_mask=row['exclusion_mask'],reciprocal_sqrt=seed)
            self.assertEqual(list(dst['data']),row['output'])
            self.assertEqual(dst['records'],row['records'])
            self.assertEqual(dst['flags'],row['flags'])
            self.assertEqual(visits,row['visits'])
            self.assertEqual(len(used),len(row['seeds']))
