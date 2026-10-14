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


class Encoding27Tests(unittest.TestCase):
    def data(self):
        return bytes([27,2,60,0])+struct.pack('<6f',1,2,3,5,-2,11)

    def test_interpolation_and_terminal_zero_fourth_lane(self):
        from engine.animation_decoder import sample_encoding_27 as vector
        self.assertEqual(vector(self.data(),.5,30)['value'],[3,0,7,0])
        self.assertEqual(vector(self.data(),1,60)['value'],[5,-2,11,0])
        self.assertEqual(vector(self.data(),-1,0)['value'],[1,2,3,0])

    def test_dispatch_uses_vector_decoder(self):
        from engine.animation_decoder import registered_channel_decoder
        resource=Resource([Channel(27,self.data(),16)])
        out=[];state=SampleState(30)
        sample_channel(resource,0,.5,out,state,registered_channel_decoder)
        self.assertEqual(out,[3,0,7,0])
        self.assertEqual(state.cursor,0)

    def test_truncation_rejected(self):
        from engine.animation_decoder import sample_encoding_27 as vector
        with self.assertRaises(ValueError):vector(self.data()[:-1],0,0)


class SerializedChannelTests(unittest.TestCase):
    def test_vector_record_offset_trailing_bytes_and_raw_copy(self):
        from engine.animation_decoder import unpack_serialized_channel, sample_encoding_27
        samples=struct.pack('<6f',1,2,3,5,6,7)
        record=bytes([27])+struct.pack('<II',123,2)+bytes([60])+samples
        decoded=unpack_serialized_channel(b'prefix'+record+b'tail',6)
        self.assertEqual(decoded['consumed'],len(record))
        self.assertEqual(decoded['opaque_allocation'],123)
        self.assertEqual(decoded['payload'][4:],samples)
        self.assertEqual(sample_encoding_27(decoded['payload'],.5,30)['value'],[3,4,5,0])

    def test_quaternion_alignment(self):
        from engine.animation_decoder import unpack_serialized_channel
        samples=struct.pack('<4f',0,0,0,1)
        result=unpack_serialized_channel(bytes([0])+struct.pack('<II',16,1)+samples)
        self.assertEqual(result['payload'][16:],samples)
        self.assertEqual(len(result['payload']),32)

    def test_unsupported_reference_and_count_and_truncation(self):
        from engine.animation_decoder import unpack_serialized_channel
        for data in (bytes([254])+bytes(12),bytes([27])+struct.pack('<II',1,256),
                     bytes([27])+struct.pack('<II',1,1)):
            with self.assertRaises(ValueError):unpack_serialized_channel(data)


class Encoding21Tests(unittest.TestCase):
    def test_packed_word_swap_and_extremes(self):
        from engine.animation_decoder import quaternion_z16
        for word in (0,16384,32767):
            a,b=quaternion_z16(word),quaternion_z16(word|32768)
            self.assertEqual(a[:2],[0,0])
            self.assertEqual(a[2:],b[2:][::-1])
            self.assertAlmostEqual(sum(x*x for x in a),1,places=6)

    def test_serialized_dispatch_and_rewind(self):
        from engine.animation_decoder import unpack_serialized_channel, registered_channel_decoder
        raw=bytes([21])+struct.pack('<II',4,2)+bytes([60])+struct.pack('<2H',16384,32767)
        decoded=unpack_serialized_channel(raw)
        self.assertEqual(decoded['consumed'],len(raw))
        resource=Resource([Channel(21,decoded['payload'],16)])
        state=SampleState(60);out=[]
        sample_channel(resource,0,1,out,state,registered_channel_decoder)
        self.assertEqual(state.cursor,1)
        state.hint=30
        sample_channel(resource,0,.5,out,state,registered_channel_decoder)
        self.assertEqual(state.cursor,0)
        self.assertEqual(out[:2],[0,0])
        self.assertAlmostEqual(sum(x*x for x in out),1,places=6)

    def test_truncated_sample(self):
        from engine.animation_decoder import sample_encoding_21
        with self.assertRaises(ValueError):sample_encoding_21(bytes([21,1]),0,0)
