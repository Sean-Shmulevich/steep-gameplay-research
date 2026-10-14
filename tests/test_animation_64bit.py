import struct
import unittest
from engine.animation_decoder import quaternion_smallest_three64, unpack_serialized_channel, sample_encoding_15, sample_encoding_16, sample_encoding_17
from engine.animation_endpoints import f32


def words(selector,values=(400000,500000,600000),unused=0):
    a,b,c=values
    packed=(selector<<62)|(unused<<60)|(a<<40)|(b<<20)|c
    return packed>>32,packed&0xffffffff


class Packed64Tests(unittest.TestCase):
    def test_all_selectors_word_order_and_unused_bits(self):
        expected=[f32(f32(v*f32(1.3487017440638738e-06))+f32(-.7071067690849304)) for v in (400000,500000,600000)]
        for index in range(4):
            value=quaternion_smallest_three64(words(index))
            self.assertEqual(value[:index]+value[index+1:],expected)
            self.assertAlmostEqual(sum(v*v for v in value),1,places=6)
            self.assertEqual(value,quaternion_smallest_three64(words(index,unused=3)))
        with self.assertRaises(ValueError):quaternion_smallest_three64([0,0])
        with self.assertRaises(ValueError):quaternion_smallest_three64([True,0])
        with self.assertRaises(ValueError):quaternion_smallest_three64(words(0),rsqrt_estimate=0)

    def test_three_timelines_equivalent(self):
        raw=struct.pack('<4I',*words(0),*words(1))
        samples=[]
        for codec,times,sampler in ((15,bytes([4]),sample_encoding_15),(16,struct.pack('<H',4),sample_encoding_16),(17,bytes([65,5]),sample_encoding_17)):
            record=struct.pack('<BII',codec,0,2)+times+raw
            payload=unpack_serialized_channel(record)['payload']
            samples.append([sampler(payload,h/60,h)['value'] for h in (0,1,2,4,2,0)])
            with self.assertRaises(ValueError):sampler(payload[:-1],0,0)
        self.assertEqual(samples[0],samples[1]);self.assertEqual(samples[0],samples[2])
