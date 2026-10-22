import json
from pathlib import Path
import struct
import unittest
from reference.animation_channel_blend import blend_channel


class ChannelBlendTests(unittest.TestCase):
    def test_instruction_receipt(self):
        data=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/channel_blend_validation.json').read_text())
        self.assertEqual(data['cases'],90)
        for row in data['rows']:
            result=bytearray([0xcd]*64)
            blend_channel(result,bytes(row['source_a']),bytes(row['source_b']),
                struct.pack('<IHH',0,16,row['kind']|0xa0),row['weight'],[row['weight']]*4,
                row['integer_weight'],quaternion_blend=lambda *a:self.fail('uncovered quaternion'))
            self.assertEqual(list(result),row['expected'])

    def test_kind_four_preserves_first_source_and_alias(self):
        a=bytearray(struct.pack('<3f',2,4,8));b=struct.pack('<3f',10,20,30)
        blend_channel(a,a,b,struct.pack('<IHH',0,0,4),.75,[.75]*4,191,
                      quaternion_blend=lambda *a:self.fail())
        self.assertEqual(struct.unpack('<3f',a),(2,4,8))

    def test_quaternion_dependency_is_explicit(self):
        out=bytearray(16);a=struct.pack('<4f',0,0,0,1);b=struct.pack('<4f',1,0,0,0)
        calls=[]
        def quaternion(x,y,w):calls.append((x,y,w));return x
        blend_channel(out,a,b,struct.pack('<IHH',0,0,6),.5,[.5]*4,127,
                      quaternion_blend=quaternion)
        self.assertEqual(out,a);self.assertEqual(len(calls),1)

    def test_quaternion_kernel_join_against_instruction_receipt(self):
        data=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/weighted_rotation_channel_validation.json').read_text())
        cases=[r for r in data['samples'] if r['inputs']['mode']==0]
        self.assertEqual(len(cases),80)
        for row in cases:
            value=row['inputs'];used=[]
            def seed(length):
                i=len(used);used.append(length)
                self.assertEqual(length,row['lengths'][i])
                return row['seeds'][i]
            first=struct.pack('<4f',*value['first']);second=struct.pack('<4f',*value['second'])
            output=bytearray(16)
            blend_channel(output,first,second,struct.pack('<IHH',0,0,6),value['weight'],
                [value['weight']]*4,0,reciprocal_sqrt=seed)
            self.assertEqual(output,struct.pack('<4f',*row['result']))
            self.assertEqual(len(used),len(row['seeds']))

    def test_missing_seed_policy_is_refused(self):
        identity=struct.pack('<4f',0,0,0,1)
        with self.assertRaisesRegex(ValueError,'seed service'):
            blend_channel(bytearray(16),identity,identity,struct.pack('<IHH',0,0,6),.5,[.5]*4,0)
