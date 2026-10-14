import struct
import unittest
from engine.animation_decoder import unpack_serialized_channel, sample_encoding_24, sample_encoding_26, sample_encoding_27, sample_encoding_29, registered_channel_decoder
from engine.animation_sampling import SampleState


class MaskFloatTests(unittest.TestCase):
    def test_equivalent_byte_and_mask_timelines(self):
        for byte,mask,sampler,masked in ((24,26,sample_encoding_24,sample_encoding_26),(27,29,sample_encoding_27,sample_encoding_29)):
            raw=struct.pack('<6f',.125,.25,.375,.25,.125,.375)
            a=unpack_serialized_channel(struct.pack('<BII',byte,0,2)+bytes([4])+raw)['payload']
            # Mode 65: one mask byte, timestamps shifted left by one.
            b=unpack_serialized_channel(struct.pack('<BII',mask,0,2)+bytes([65,5])+raw)['payload']
            for hint in (0,1,2,3,4,2,0):
                expected=sampler(a,hint/60,hint)['value']
                self.assertEqual(masked(b,hint/60,hint,0xffffffff)['value'],expected)
                out=[];state=SampleState(hint,10000)
                registered_channel_decoder(mask,b,16,hint/60,out,state)
                self.assertEqual(out,expected)
            with self.assertRaises(ValueError):masked(b[:-1],0,0)

    def test_vector_fourth_lane_and_no_normalization(self):
        raw=struct.pack('<6f',10,20,30,20,40,60)
        p=unpack_serialized_channel(struct.pack('<BII',29,0,2)+bytes([1,5])+raw)['payload']
        self.assertEqual(sample_encoding_29(p,1/60,1)['value'],[15,30,45,0])
        self.assertEqual(sample_encoding_29(p,1,2)['value'],[20,40,60,0])
