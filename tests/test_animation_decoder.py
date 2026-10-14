import math
import struct
import unittest
from engine.animation_decoder import sample_encoding_zero as sample, encoding_zero_decoder
from engine.animation_sampling import Channel, Resource, SampleState, sample_channel


def payload(ticks, values):
    data = bytearray((len(values)+16)&~15)
    data[1] = len(values)
    data[2:len(values)+1] = bytes(ticks)
    return bytes(data)+b''.join(struct.pack('<4f',*v) for v in values)


class EncodingZeroTests(unittest.TestCase):
    def test_single_key_is_copied_without_normalization(self):
        result=sample(payload([],[(2,0,0,0)]),100,6000)
        self.assertEqual(result['value'],[2,0,0,0])
        self.assertIsNone(result['weight'])

    def test_sixty_hz_midpoint_and_rewind(self):
        data=payload([60],[(0,0,0,1),(0,0,1,0)])
        end=sample(data,1,60)
        self.assertEqual(end['cursor'],1)
        middle=sample(data,.5,30,end['cursor'])
        self.assertEqual(middle['path'],'binary')
        self.assertEqual(middle['weight'],.5)
        self.assertAlmostEqual(middle['value'][2],math.sqrt(.5),places=6)
        self.assertAlmostEqual(middle['value'][3],math.sqrt(.5),places=6)

    def test_float_time_is_clamped_independently_of_hint(self):
        data=payload([60],[(0,0,0,1),(0,0,1,0)])
        self.assertEqual(sample(data,-1,30)['weight'],0)
        self.assertEqual(sample(data,2,30)['weight'],1)

    def test_resource_dispatch_to_real_decoder_and_failure_atomicity(self):
        data=payload([60],[(0,0,0,1),(0,0,1,0)])
        end=Resource([Channel(0,data,16)])
        start=Resource([Channel('unused',None,16)],8,[1],end)
        out=[];state=SampleState(30)
        self.assertEqual(sample_channel(start,0,.5,out,state,encoding_zero_decoder),2)
        self.assertEqual(len(out),4)
        self.assertEqual(state.cursor,0)
        before=out[:]
        with self.assertRaises(ValueError):
            encoding_zero_decoder(0,data[:-1],16,.5,out,state)
        self.assertEqual(out,before)
        self.assertEqual(state.cursor,0)

    def test_bad_headers_and_truncation(self):
        for data in (b'',b'\x00\x00',b'\x01\x01'+bytes(30),b'\x00\x01'):
            with self.assertRaises(ValueError):sample(data,0,0)
