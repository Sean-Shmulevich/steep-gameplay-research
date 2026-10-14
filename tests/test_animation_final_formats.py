import struct
import unittest
from engine.animation_decoder import unpack_serialized_channel, sample_encoding_39, sample_encoding_40, sample_encoding_41, sample_encoding_66, registered_channel_decoder
from engine.animation_sampling import SampleState


class FinalFormatTests(unittest.TestCase):
    def test_scalar_timelines_and_signed_values(self):
        results=[]
        for codec,times,fn in ((39,bytes([4]),sample_encoding_39),(40,struct.pack('<H',4),sample_encoding_40),(41,bytes([65,5]),sample_encoding_41)):
            record=struct.pack('<BII',codec,0,2)+times+struct.pack('<2b',-128,127)
            p=unpack_serialized_channel(record)['payload']
            results.append([fn(p,t/60,t)['value'] for t in (0,1,2,4,1)])
            out=[];state=SampleState(2)
            registered_channel_decoder(codec,p,4,2/60,out,state)
            self.assertEqual(out,results[-1][2])
            with self.assertRaises(ValueError):fn(p[:-1],0,0)
        self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])

    def test_opaque_copy_uses_hint_not_float_time(self):
        first=0xffffffffffffffff;second=0x0123456789abcdef
        record=struct.pack('<BIIBQQ',66,0,2,60,first,second)
        p=unpack_serialized_channel(record)['payload']
        self.assertEqual(sample_encoding_66(p,100,30)['value'],[first])
        self.assertEqual(sample_encoding_66(p,0,60)['value'],[second])
        self.assertEqual(sample_encoding_66(p,0,0,1)['value'],[first])
        self.assertIsNone(sample_encoding_66(p,.5,30)['weight'])
        out=[];state=SampleState(60)
        registered_channel_decoder(66,p,8,0,out,state)
        self.assertEqual(out,[second])
        with self.assertRaises(ValueError):registered_channel_decoder(66,p,16,0,out,state)
        with self.assertRaises(ValueError):sample_encoding_66(p[:-1],0,0)
