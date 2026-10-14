import struct
import unittest
from engine.animation_decoder import unpack_serialized_channel, sample_encoding_9, sample_encoding_10, sample_encoding_12, sample_encoding_13, sample_encoding_21, sample_encoding_22, sample_encoding_24, sample_encoding_25, registered_channel_decoder
from engine.animation_sampling import SampleState


class WideQuaternionTests(unittest.TestCase):
    def test_byte_wide_equivalence_across_sample_and_rewind(self):
        for byte,wide,small,large,raw in (
            (9,10,sample_encoding_9,sample_encoding_10,struct.pack('<2I',0x5ff7fdff,0x9ff7fdff)),
            (12,13,sample_encoding_12,sample_encoding_13,struct.pack('<6H',16384,16384,16384,49152,16384,16384)),
            (21,22,sample_encoding_21,sample_encoding_22,struct.pack('<2H',10000,40000)),
            (24,25,sample_encoding_24,sample_encoding_25,struct.pack('<6f',.125,.25,.375,.25,.125,.375))):
            a=unpack_serialized_channel(struct.pack('<BII',byte,0,2)+bytes([60])+raw)['payload']
            b=unpack_serialized_channel(struct.pack('<BIIH',wide,0,2,60)+raw)['payload']
            cursor=0xffffffff
            for hint in (0,15,30,45,60,30,0):
                expected=small(a,hint/60,hint)['value'];result=large(b,hint/60,hint,cursor)
                self.assertEqual(result['value'],expected);cursor=result['cursor']
                output=[];state=SampleState(hint)
                registered_channel_decoder(wide,b,16,hint/60,output,state)
                self.assertEqual(output,expected)
            with self.assertRaises(ValueError):large(b[:-1],0,0)

    def test_extended_count_and_final_key(self):
        for codec,sampler,raw in ((10,sample_encoding_10,struct.pack('<I',0x5ff7fdff)),(13,sample_encoding_13,struct.pack('<3H',16384,16384,16384)),(22,sample_encoding_22,struct.pack('<H',40000)),(25,sample_encoding_25,struct.pack('<3f',.125,.25,.375))):
            record=struct.pack('<BII',codec,0,256)+struct.pack('<255H',*range(2,512,2))+raw*256
            payload=unpack_serialized_channel(record)['payload']
            self.assertEqual(payload[1],0)
            first=sampler(payload,0,0)
            last=sampler(payload,9,510)
            self.assertEqual(last['cursor'],255)
            self.assertEqual(last['value'],first['value'])
            self.assertIsNone(last['weight'])
