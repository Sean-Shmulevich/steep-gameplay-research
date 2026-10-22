import json
from pathlib import Path
import struct
import unittest
from reference.animation_channel_blend import blend_additive_channel

ROOT=Path(__file__).resolve().parents[1]


class AdditiveChannelTests(unittest.TestCase):
    def test_typed_instruction_receipt(self):
        r=json.loads((ROOT/'native/snow_host/additive_channel_blend_validation.json').read_text())
        self.assertEqual(r['cases'],90)
        for row in r['rows']:
            dst=bytearray([205]*64)
            blend_additive_channel(dst,bytes(row['source_a']),bytes(row['source_b']),
                struct.pack('<IHH',0,16,row['kind']|0xa0),row['weight'],row['vector_weight'],row['integer_weight'])
            self.assertEqual(list(dst),row['expected'])

    def test_existing_rotation_instruction_receipt(self):
        r=json.loads((ROOT/'native/snow_host/weighted_rotation_channel_validation.json').read_text())
        rows=[s for s in r['samples'] if s['inputs']['mode']==4]
        self.assertEqual(len(rows),80)
        for row in rows:
            inputs=row['inputs'];used=[]
            def seed(n):
                i=len(used);used.append(n);self.assertEqual(n,row['lengths'][i]);return row['seeds'][i]
            dst=bytearray([205]*48)
            a=bytes(16)+struct.pack('<4f',*inputs['first'])+bytes(16)
            b=bytes(16)+struct.pack('<4f',*inputs['second'])+bytes(16)
            blend_additive_channel(dst,a,b,struct.pack('<IHH',0,16,6),inputs['weight'],[99]*4,0,
                reciprocal_sqrt=seed)
            self.assertEqual(dst[16:32],struct.pack('<4f',*row['result']))
            self.assertEqual(dst[:16]+dst[32:],bytes([205]*32))
            self.assertEqual(len(used),len(row['seeds']))
