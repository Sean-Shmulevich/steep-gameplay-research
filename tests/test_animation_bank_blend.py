import json
from pathlib import Path
import unittest
from reference.animation_bank_blend import blend_regular_pose_bank


class BankBlendTests(unittest.TestCase):
    def test_joined_instruction_receipt(self):
        r=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/regular_bank_blend_validation.json').read_text())
        self.assertEqual(r['cases'],20)
        for row in r['rows']:
            dst=dict(data=bytearray([0xcd]*64),profile=r['profile'],flags=0)
            a=dict(data=bytes(r['first']),profile=r['profile'])
            b=dict(data=bytes(r['second']),profile=r['profile'])
            masks=[]
            visits=blend_regular_pose_bank(dst,a,b,row['weight'],0,row['mask'],
                exclusion_mask=row['exclusion_mask'],
                supplemental=lambda d,a,b,m,w,mode:masks.append(m))
            self.assertEqual(list(dst['data']),row['output'])
            self.assertEqual(dst['flags'],row['flags'])
            self.assertEqual(masks,row['supplemental_masks'])
            self.assertEqual(visits,row['visits'])

    def test_near_one_copies_kind_three_but_arithmetic_does_not(self):
        profile=dict(group_count=0,channel_count=1,descriptors=[dict(offset=0,kind=3)])
        first=dict(profile=profile,data=b'aaaa');second=dict(profile=profile,data=b'bbbb')
        for weight,expected,flags in ((.5,b'cccc',0),(1,b'bbbb',1<<27)):
            destination=dict(profile=profile,data=bytearray(b'cccc'),flags=0)
            blend_regular_pose_bank(destination,first,second,weight,0,65535,
                                    supplemental=lambda *a:None)
            self.assertEqual(destination['data'],expected);self.assertEqual(destination['flags'],flags)

    def test_joined_supplemental_instruction_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/regular_bank_supplemental_validation.json').read_text())
        self.assertEqual(receipt['cases'],20)
        for row in receipt['rows']:
            profile=receipt['profile']
            def record(vector):return dict(id=7,vector=vector,rotation=[0,0,0,1])
            dst=dict(data=bytearray([0xcd]*64),profile=profile,flags=0,records=[record([-1]*4)])
            a=dict(data=bytes(receipt['first']),profile=profile,records=[record([1,2,3,4])])
            b=dict(data=bytes(receipt['second']),profile=profile,records=[record([5,6,7,8])])
            visits=blend_regular_pose_bank(dst,a,b,row['weight'],0,row['mask'],
                exclusion_mask=row['exclusion_mask'],
                reciprocal_sqrt=lambda n:self.fail('identity rotation needs no seed'))
            self.assertEqual(dst['records'],row['records'])
            self.assertEqual(list(dst['data']),row['output'])
            self.assertEqual(dst['flags'],row['flags']);self.assertEqual(visits,row['visits'])

    def test_implicit_missing_record_data_is_refused(self):
        state=dict(data=bytearray(16),flags=0,profile={})
        with self.assertRaisesRegex(ValueError,'record lists'):
            blend_regular_pose_bank(state,state,state,.5,0,65535)

    def test_joined_channel_and_supplemental_rotations(self):
        import struct
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/regular_bank_rotation_join_validation.json').read_text())
        self.assertEqual(receipt['cases'],90)
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
            visits=blend_regular_pose_bank(dst,a,b,row['weight'],0,row['mask'],
                exclusion_mask=row['exclusion_mask'],reciprocal_sqrt=seed)
            self.assertEqual(list(dst['data']),row['output'])
            self.assertEqual(dst['records'],row['records'])
            self.assertEqual(dst['flags'],row['flags'])
            self.assertEqual(visits,row['visits'])
            self.assertEqual(len(used),len(row['seeds']))

    def test_in_place_channel_and_supplemental_rotations(self):
        import struct
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/regular_bank_rotation_alias_validation.json').read_text())
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
            a=dict(data=bytearray(receipt['first']),profile=profile,flags=0,
                   records=[record([1,2,3,4],[0,0,0,1])])
            b=dict(data=bytearray(bytes([20]*64)+struct.pack('<4f',*rotation)),profile=profile,flags=0,
                   records=[record([5,6,7,8],rotation)])
            dst=a if row['alias']=='first' else b
            visits=blend_regular_pose_bank(dst,a,b,row['weight'],0,row['mask'],
                exclusion_mask=row['exclusion_mask'],reciprocal_sqrt=seed)
            self.assertEqual(list(dst['data']),row['output'])
            self.assertEqual(dst['records'],row['records'])
            self.assertEqual(dst['flags'],row['flags'])
            self.assertEqual(visits,row['visits'])
            self.assertEqual(len(used),len(row['seeds']))
