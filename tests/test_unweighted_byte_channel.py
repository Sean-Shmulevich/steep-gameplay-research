import json
from pathlib import Path
import struct
import unittest
from reference.animation_channel_blend import combine_unweighted_byte_channel, blend_additive_channel
from reference.animation_channels import plan_arithmetic_channel_route


class UnweightedByteTests(unittest.TestCase):
    def test_complete_typed_instruction_receipt(self):
        r=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/unweighted_byte_channel_validation.json').read_text())
        self.assertEqual(r['cases'],96)
        for row in r['rows']:
            dst=bytearray([205]*64)
            combine_unweighted_byte_channel(dst,bytes(row['source_a']),bytes(row['source_b']),
                struct.pack('<IHH',0,16,row['kind']|0xa0))
            self.assertEqual(list(dst),row['expected'])

    def test_near_one_scalar_discontinuity(self):
        a=struct.pack('<f',2.);b=struct.pack('<f',8.);desc=struct.pack('<IHH',0,0,1)
        results=[]
        for weight in (.999,1.):
            dst=bytearray(4);route=plan_arithmetic_channel_route(4,weight,False,[1],0)
            if route['helper']=='unweighted_combine':combine_unweighted_byte_channel(dst,a,b,desc)
            else:blend_additive_channel(dst,a,b,desc,weight,[weight]*4,int(weight*255))
            results.append(struct.unpack('<f',dst)[0])
        self.assertLess(results[0],8.);self.assertEqual(results[1],10.)

    def test_in_place_reads_before_write(self):
        data=bytearray(struct.pack('<4f',1,2,3,4));b=struct.pack('<4f',5,6,7,8)
        combine_unweighted_byte_channel(data,data,b,struct.pack('<IHH',0,0,5))
        self.assertEqual(struct.unpack('<4f',data),(6.,8.,10.,12.))
