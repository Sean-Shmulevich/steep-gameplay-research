import struct
import unittest
from engine.animation_decoder import unpack_serialized_channel, sample_encoding_39, sample_encoding_54, registered_channel_decoder
from engine.animation_sampling import SampleState
from engine.animation_endpoints import f32


def payload(codec,values):
    fmt='b' if codec==39 else 'I'
    record=struct.pack('<BII',codec,0,len(values))+bytes([60]*(len(values)-1))+struct.pack('<'+fmt*len(values),*values)
    return unpack_serialized_channel(record)['payload']


class ScalarTests(unittest.TestCase):
    def test_signed_byte_scale_clamp_and_rewind(self):
        p=payload(39,[-128,127])
        self.assertEqual(sample_encoding_39(p,0,0)['value'],[f32(-128*f32(.008))])
        self.assertEqual(sample_encoding_39(p,1,60)['value'],[f32(127*f32(.008))])
        self.assertEqual(sample_encoding_39(p,-1,0,1)['value'],sample_encoding_39(p,0,0)['value'])
        self.assertAlmostEqual(sample_encoding_39(p,.5,30)['value'][0],-.004,places=6)

    def test_unsigned_interpolation_wrap_and_round(self):
        self.assertEqual(sample_encoding_54(payload(54,[0,3]),.5,30)['value'],[2])
        # Native SUB EAX zero-extends before signed 64-bit CVTSI2SS.
        self.assertEqual(sample_encoding_54(payload(54,[10,9]),.5,30)['value'],[2147483658])
        self.assertEqual(sample_encoding_54(payload(54,[10,9]),1,60)['value'],[9])
        self.assertEqual(sample_encoding_54(payload(54,[0xffffffff]),0,0)['value'],[0xffffffff])

    def test_scalar_dispatch_width_and_failure_atomicity(self):
        for codec in (39,54):
            p=payload(codec,[1,3]);out=[];state=SampleState(30)
            registered_channel_decoder(codec,p,4,.5,out,state)
            self.assertEqual(len(out),1)
            old=out[:];cursor=state.cursor
            with self.assertRaises(ValueError):registered_channel_decoder(codec,p,16,.5,out,state)
            with self.assertRaises(ValueError):registered_channel_decoder(codec,p[:-1],4,.5,out,state)
            self.assertEqual(out,old);self.assertEqual(state.cursor,cursor)
