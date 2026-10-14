import bisect
import struct
import unittest
from engine.animation_key_selection import select_wide_key
from engine.animation_decoder import unpack_serialized_channel, sample_encoding_28, wide_channel_layout


class WideTests(unittest.TestCase):
    def test_selection_oracle_duplicates_rewinds_and_large_ticks(self):
        times=[0]+[i*100 for i in range(1,300)]+[29900,65535]
        for cursor in (0,1,255,299,300,301,0xffffffff):
            for hint in (0,1,99,100,25500,29900,40000,65534,65535,0xffffffff):
                result=select_wide_key(len(times),times[1:],hint,cursor)
                index=bisect.bisect_right(times,hint)-1
                self.assertEqual(result['cursor'],index)
                packed=times[index]|(times[index+1]<<16 if index+1<len(times) else 0)
                self.assertEqual(result['packed_ticks'],packed)
        for args in ((65536,[],0),(2,[65536],0),(3,[4,3],0),(1,[], -1)):
            with self.assertRaises(ValueError):select_wide_key(*args)

    def test_short_extended_header_boundary_and_final_key(self):
        for count in (1,255,256,300):
            record=struct.pack('<BII',28,0,count)+struct.pack('<'+'H'*(count-1),*range(1,count))+b''.join(struct.pack('<3f',i,2*i,3*i) for i in range(count))
            parsed=unpack_serialized_channel(record);p=parsed['payload']
            self.assertEqual(parsed['consumed'],len(record))
            self.assertEqual(p[1],count if count<256 else 0)
            self.assertEqual(wide_channel_layout(p)[0],count)
            self.assertEqual(sample_encoding_28(p,100,count-1)['value'],[count-1,2*(count-1),3*(count-1),0])
            self.assertEqual(sample_encoding_28(p,0,0,count-1)['value'],[0,0,0,0])
            with self.assertRaises(ValueError):sample_encoding_28(p[:-1],0,0)

    def test_long_timestamp_interpolation_and_validation(self):
        record=struct.pack('<BIIH6f',28,0,2,600,10,20,30,20,40,60)
        p=unpack_serialized_channel(record)['payload']
        self.assertEqual(sample_encoding_28(p,5,300)['value'],[15,30,45,0])
        with self.assertRaises(ValueError):sample_encoding_28(p,float('nan'),0)
        with self.assertRaises(ValueError):unpack_serialized_channel(record[:-1])
        with self.assertRaises(ValueError):wide_channel_layout(bytes([28,0,0,0]))
