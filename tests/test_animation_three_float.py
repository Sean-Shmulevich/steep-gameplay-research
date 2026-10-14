import math
import struct
import unittest
from engine.animation_decoder import quaternion_three_floats, sample_encoding_24, unpack_serialized_channel, registered_channel_decoder
from engine.animation_sampling import SampleState


class ThreeFloatTests(unittest.TestCase):
    def test_selectors_preserve_low_bits_and_component_order(self):
        base=struct.unpack('<3I',struct.pack('<3f',.125,-.25,.375))
        for selector in range(4):
            words=[base[0]|(selector&1),base[1]|(selector>>1),base[2]|1]
            stored=list(struct.unpack('<3f',struct.pack('<3I',*words)))
            q=quaternion_three_floats(words)
            self.assertEqual(q[:selector]+q[selector+1:],stored)
            self.assertGreater(q[selector],0)
            self.assertAlmostEqual(sum(v*v for v in q),1,places=6)
            self.assertNotEqual(q,quaternion_three_floats(words,rsqrt_estimate=.5))

    def test_serialized_sampling_and_dispatch(self):
        words=struct.unpack('<3I',struct.pack('<3f',.125,.25,.375))
        record=struct.pack('<BII',24,0,2)+bytes([60])+struct.pack('<6I',*words,words[0]|1,words[1],words[2])
        parsed=unpack_serialized_channel(record)
        self.assertEqual(parsed['consumed'],len(record))
        payload=parsed['payload']
        self.assertEqual(sample_encoding_24(payload,0,0)['value'],quaternion_three_floats(words))
        midpoint=sample_encoding_24(payload,.5,30)
        self.assertEqual(midpoint['weight'],.5)
        self.assertTrue(all(math.isfinite(v) for v in midpoint['value']))
        state=SampleState(30);out=[]
        registered_channel_decoder(24,payload,16,.5,out,state)
        self.assertEqual(out,midpoint['value'])
        end=sample_encoding_24(payload,1,60)
        self.assertEqual(sample_encoding_24(payload,0,0,end['cursor'])['value'],quaternion_three_floats(words))
        with self.assertRaises(ValueError):unpack_serialized_channel(record[:-1])
        with self.assertRaises(ValueError):sample_encoding_24(payload[:-1],0,0)

    def test_invalid_words_and_radicands(self):
        for words in ([0,0],[True,0,0],[-1,0,0],[0x7f800000,0,0],[0x3f800000,0,0]):
            with self.assertRaises(ValueError):quaternion_three_floats(words)
        with self.assertRaises(ValueError):quaternion_three_floats([0,0,0],rsqrt_estimate=0)
