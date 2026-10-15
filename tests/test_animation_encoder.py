import math
import random
import struct
import unittest
from engine import animation_decoder as decoder
from engine.animation_container import parse_clip_body
from engine.animation_encoder import (KINDS, VALUE_ENCODINGS, build_channel, build_clip, build_track, channel_values,
    choose_mask_mode, decode_sample, default_allocation, encode_value, make_channel, parse_channel,
    parse_clip, sample_bytes, scale_quaternion_rotation, scale_rotation_amplitude)

RUNTIME=VALUE_ENCODINGS
QUAT_STEP = {'s32': 1.4142135/1022, 's48': 1.4142135/32767, 's64': 1.4142135/1048575, 'sfl': 3e-7, 'z16': 1.4142135/32767}


def obj(kind):return struct.pack('<BQI',0,0,kind)


def clip_body(records,ids=None):
    """Synthetic version-2 clip body (layout from the container tests' fixture)."""
    ids=ids or list(range(10,10+len(records)))
    result=struct.pack('<QIBfI',7,0x0fa3067f,1,1.,11)+struct.pack('<III',12,0,0)+bytes(4)+struct.pack('<I',0)
    result+=obj(0x0181efe8)+struct.pack('<II',11,len(records))
    for i in ids:result+=struct.pack('<QII',0,0x653caa76,i)
    result+=struct.pack('<H',0)+struct.pack('<II',4,0x653caa76)+struct.pack('<II',5,len(records))
    return result+b''.join(records)


def runtime_sample(channel,hint=0,time=0.0):
    """Round trip through the real serialized adapter and the sampler named for the tag."""
    parsed=decoder.unpack_serialized_channel(build_channel(channel))
    name='zero' if channel['encoding']==0 else str(channel['encoding'])
    return getattr(decoder,'sample_encoding_'+name)(parsed['payload'],time,hint)


def unit(*v):
    n=math.sqrt(sum(x*x for x in v));return [x/n for x in v]


class StructuralTests(unittest.TestCase):
    def sample_values(self,encoding,count):
        kind=KINDS[encoding];r=random.Random(encoding*1000+count)
        if kind in ('f4','s32','s48','s64','sfl'):
            return [unit(*[r.gauss(0,1) for _ in range(4)]) for _ in range(count)]
        if kind=='z16':return [unit(0,0,r.gauss(0,1),r.gauss(0,1)) for _ in range(count)]
        if kind=='vec3':return [[r.uniform(-9,9) for _ in range(3)]+[0.0] for _ in range(count)]
        if kind=='s8':return [[r.randrange(-128,128)*.008] for _ in range(count)]
        if kind=='u32':return [[r.randrange(1<<32)] for _ in range(count)]
        return [[r.randrange(1<<64)] for _ in range(count)]

    def ticks(self,encoding,count):
        step=4 if encoding%3==2 else 3
        return [i*step for i in range(count)]

    def test_every_supported_encoding_is_byte_exact_through_parse_build(self):
        for encoding in VALUE_ENCODINGS:
            for count in (1,2,5,31):
                ch=make_channel(encoding,self.ticks(encoding,count),self.sample_values(encoding,count))
                data=build_channel(ch)
                parsed=parse_channel(b'xy'+data+b'tail',2)
                self.assertEqual(parsed['consumed'],len(data))
                self.assertEqual(build_channel(parsed),data,(encoding,count))
                self.assertEqual(parsed['ticks'],ch['ticks'])
                # The real decoder's adapter accepts it and sees the same bytes.
                self.assertEqual(decoder.unpack_serialized_channel(data)['consumed'],len(data))

    def test_default_allocation_equals_runtime_payload_size(self):
        for encoding in VALUE_ENCODINGS:
            for count in (1,2,9,40):
                ch=make_channel(encoding,self.ticks(encoding,count),self.sample_values(encoding,count))
                parsed=decoder.unpack_serialized_channel(build_channel(ch))
                self.assertEqual(parsed['opaque_allocation'],len(parsed['payload']),(encoding,count))

    def test_decode_of_encode_within_quantisation_and_exact_formats(self):
        for encoding in VALUE_ENCODINGS:
            kind=KINDS[encoding];values=self.sample_values(encoding,4)
            ch=make_channel(encoding,self.ticks(encoding,4),values)
            for i,v in enumerate(channel_values(ch)):
                if kind in QUAT_STEP:
                    tolerance=3*QUAT_STEP[kind]/2+2e-6
                    sign=1 if sum(a*b for a,b in zip(v,values[i]))>=0 else -1     # q and -q are one rotation
                    self.assertTrue(max(abs(a-sign*b) for a,b in zip(v,values[i]))<=tolerance,(encoding,i))
                elif kind=='s8':self.assertAlmostEqual(v[0],values[i][0],delta=1e-6)
                elif kind in ('f4','vec3'):self.assertEqual(v,[f32(x) for x in values[i]])
                else:self.assertEqual(v,values[i])

    def test_runtime_sampler_returns_encoded_key_values(self):
        values=[unit(0,0,1,1),unit(0,0,-1,2),unit(0,0,.2,1)]
        for encoding in (0,9,10,11,12,13,14,15,16,17,21,22,23,24,25,26):
            ticks=[0,2,8]
            ch=make_channel(encoding,ticks,values)
            for key,tick in enumerate(ticks):
                got=runtime_sample(ch,tick,tick/60)['value']
                want=channel_values(ch)[key]
                self.assertTrue(max(abs(a-b) for a,b in zip(got,want))<1e-6,(encoding,key))

    def test_byte_and_wide_time_boundaries(self):
        value=[[1.,2.,3.,0.]]*3
        ok=make_channel(27,[0,255,255],value)
        self.assertEqual(parse_channel(build_channel(ok))['ticks'],[0,255,255])
        for ticks in ([0,256,257],[1,2,3],[0,5,4]):
            with self.assertRaises(ValueError):build_channel(make_channel(27,ticks,value))
        wide=make_channel(28,[0,255,65535],value)
        self.assertEqual(parse_channel(build_channel(wide))['ticks'],[0,255,65535])
        with self.assertRaises(ValueError):build_channel(make_channel(28,[0,2,65536],value))
        self.assertEqual(decoder.unpack_serialized_channel(build_channel(make_channel(28,[0,1,2],value)))['encoding'],28)

    def test_wide_times_with_extended_count_header(self):
        count=300;values=[[float(i),0.,0.,0.] for i in range(count)]
        ch=make_channel(28,list(range(0,count*3,3)),values)
        data=build_channel(ch);parsed=decoder.unpack_serialized_channel(data)
        self.assertEqual(parsed['payload'][:4],bytes([28,0])+struct.pack('<H',count))
        self.assertEqual(build_channel(parse_channel(data)),data)
        got=decoder.sample_encoding_28(parsed['payload'],30*3/60,90)
        self.assertEqual(got['cursor'],30);self.assertEqual(got['value'][0],30.0)
        with self.assertRaises(ValueError):build_channel(make_channel(28,list(range(65536)),[[0.,0.,0.,0.]]*65536))

    def test_byte_time_count_limit(self):
        make=lambda n:make_channel(27,[0]*n,[[0.,0.,0.,0.]]*n)
        self.assertEqual(len(parse_channel(build_channel(make(255)))['samples']),255)
        with self.assertRaises(ValueError):build_channel(make(256))

    def test_empty_and_single_key_channels(self):
        with self.assertRaises(ValueError):build_channel(make_channel(27,[],[]))
        with self.assertRaises(ValueError):make_channel(27,[0],[])      # ticks without values
        for encoding in VALUE_ENCODINGS:
            ch=make_channel(encoding,[0],self.sample_values(encoding,1))
            data=build_channel(ch)
            self.assertEqual(parse_channel(data)['ticks'],[0])
            self.assertEqual(build_channel(parse_channel(data)),data)
            self.assertIsNone(runtime_sample(ch,0,0.)['weight'] if encoding in RUNTIME else None)

    def test_mask_modes_shift_size_and_rejections(self):
        self.assertEqual(choose_mask_mode([0]),1)
        self.assertEqual(choose_mask_mode([0,8,16]),3)
        self.assertEqual(choose_mask_mode([0,8*63-1]),63)
        self.assertEqual(choose_mask_mode([0,1,62*8+7]),63)           # last bit of the widest mask, shift zero
        self.assertEqual(choose_mask_mode([0,4*8*63-4*1]) >> 6,2)     # forced to shift two
        self.assertEqual(choose_mask_mode([0,8*504-8]) >> 6,3)
        for ticks in ([],[1],[0,0],[0,2,1],[0,8*504]):
            with self.assertRaises(ValueError):choose_mask_mode(ticks)
        # explicit mode (including spare mask bytes and shift) is preserved byte for byte
        for mode in (4,(1<<6)|9,(3<<6)|63):
            ch=make_channel(41,[0,8<<(mode>>6)],[[0.],[1.]] ,mode=mode)
            again=parse_channel(build_channel(ch))
            self.assertEqual(again['mode'],mode);self.assertEqual(again['ticks'],ch['ticks'])
        with self.assertRaises(ValueError):build_channel(make_channel(41,[0,100],[[0.],[1.]],mode=2))

    def test_unsupported_framed_family_round_trips_structurally(self):
        # Tag 33 is family 11 (six-byte elements) with byte times: framed, but no value decoder.
        data=bytes([33])+struct.pack('<II',2*6,2)+bytes([5])+bytes(range(12))
        ch=parse_channel(data)
        self.assertEqual(build_channel(ch),data)
        with self.assertRaises(ValueError):channel_values(ch)
        with self.assertRaises(ValueError):decoder.unpack_serialized_channel(data)


def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]


class QuantisedFormatTests(unittest.TestCase):
    def test_z16_every_word_is_idempotent_except_exact_ties(self):
        ties=[]
        for word in range(65536):
            raw=struct.pack('<H',word);value=decode_sample(21,raw)
            self.assertAlmostEqual(sum(v*v for v in value),1,places=6)
            if encode_value(21,value)!=raw:ties.append(word)
            self.assertEqual(encode_value(21,value,like=raw),raw)
        # Only the extreme words, where |z| and |w| are equal to float precision, may differ.
        self.assertTrue(all((w&32767) in (32767,0) or (w&32767)>=32766 for w in ties),ties)
        self.assertLess(len(ties),8)

    def test_z16_boundaries_and_restriction(self):
        self.assertEqual(encode_value(21,[0,0,0,1]),struct.pack('<H',decode_index(0.0)))
        lo,hi=decode_sample(21,struct.pack('<H',0)),decode_sample(21,struct.pack('<H',32767))
        self.assertAlmostEqual(lo[2],-.70710677,places=6);self.assertAlmostEqual(hi[2],.70710677,delta=5e-5)
        half=math.sqrt(.5)
        self.assertEqual(encode_value(21,[0,0,half,half]),struct.pack('<H',decode_index(half)))   # w omitted, z stored
        for z in (9,-9):                                                                # z omitted: flag bit, stored w = 0
            self.assertEqual(encode_value(21,[0,0,z,0]),struct.pack('<H',32768|decode_index(0.0)))
        self.assertEqual(encode_value(21,[0,0,1,2]),encode_value(21,[0,0,-1,-2]))   # q and -q share a word
        with self.assertRaises(ValueError):encode_value(21,[.1,0,0,1])
        with self.assertRaises(ValueError):encode_value(21,[0,0,0,0])

    def test_smallest_three_all_omitted_positions_negation_and_clamp(self):
        for encoding in (9,12,15,24):
            for missing in range(4):
                q=[.1,.2,.3,.4];q[missing]=2.0;q=unit(*q)
                raw=encode_value(encoding,q)
                self.assertEqual(raw,encode_value(encoding,[-v for v in q]))
                value=decode_sample(encoding,raw)
                self.assertTrue(max(abs(a-b) for a,b in zip(value,q))<.002)
                self.assertEqual(encode_value(encoding,value),raw)
        # identity and the 180 degree extremes
        for encoding in (9,12,15,24):
            self.assertAlmostEqual(decode_sample(encoding,encode_value(encoding,[0,0,0,1]))[3],1,places=6)
            for q in ([1,0,0,0],[0,1,0,0],[0,0,1,0],[.5,.5,.5,.5],[-.5,-.5,-.5,-.5]):
                value=decode_sample(encoding,encode_value(encoding,q))
                self.assertTrue(abs(abs(sum(a*b for a,b in zip(value,q)))-1)<1e-4,(encoding,q))

    def test_smallest_three_random_idempotence_with_like_and_tie_budget(self):
        r=random.Random(5)
        for encoding in (9,12,15,24):
            differing=0
            for _ in range(4000):
                raw=encode_value(encoding,[r.gauss(0,1) for _ in range(4)]);value=decode_sample(encoding,raw)
                again=encode_value(encoding,value,like=raw);self.assertEqual(again,raw)
                differing+=encode_value(encoding,value)!=raw
            self.assertLess(differing,40,encoding)    # near-tie omitted-lane choices only

    def test_decoded_words_with_unused_bits_survive_with_like(self):
        raw=struct.pack('<3H',12000,17000,21000|32768)
        value=decode_sample(12,raw)
        self.assertNotEqual(encode_value(12,value),raw)           # spare bit is not derivable from values
        self.assertEqual(encode_value(12,value,like=raw),raw)
        high,low=struct.unpack('<2I',encode_value(15,unit(.1,.2,.3,.9)))
        raw=struct.pack('<2I',high|(3<<28),low)                    # bits 60-61 are unused in the 64-bit word
        value=decode_sample(15,raw)
        self.assertNotEqual(encode_value(15,value),raw)
        self.assertEqual(encode_value(15,value,like=raw),raw)

    def test_three_float_selector_bits_live_in_mantissa(self):
        for missing in range(4):
            q=[.1,.2,.3,.4];q[missing]=3.;q=unit(*q)
            words=struct.unpack('<3I',encode_value(24,q))
            self.assertEqual((words[0]&1)|((words[1]&1)<<1),missing)

    def test_scalar_byte_saturation(self):
        for value,expected in ((0,0),(.008,1),(-1.024,-128),(-5,-128),(1.016,127),(9,127)):
            self.assertEqual(struct.unpack('<b',encode_value(39,[value]))[0],expected)
        for index in range(-128,128):
            raw=struct.pack('<b',index);self.assertEqual(encode_value(39,decode_sample(39,raw)),raw)
        with self.assertRaises(ValueError):encode_value(39,[float('nan')])

    def test_float_and_integer_formats_reject_bad_input(self):
        for encoding,value in ((27,[float('inf'),0,0,0]),(27,[1,2,3,4]),(0,[1,2,3]),(54,[-1]),(54,[1<<32]),(66,[1<<64]),(54,[1.5]),(21,[0,0,float('nan'),1])):
            with self.assertRaises(ValueError):encode_value(encoding,value)
        for encoding in (54,66):
            raw=bytes(range(1,sample_bytes(encoding)+1));self.assertEqual(encode_value(encoding,decode_sample(encoding,raw)),raw)
        zero=struct.pack('<4f',2,0,0,0);self.assertEqual(encode_value(0,decode_sample(0,zero)),zero)  # no normalisation


def decode_index(value):
    return round((value+.7071067690849304)/4.316100603318773e-05)


class ClipTests(unittest.TestCase):
    def records(self):
        q=make_channel(12,[0,6,12],[unit(0,0,.2,1),unit(.3,0,.1,1),unit(0,.5,0,1)])
        v=make_channel(27,[0],[[1.,2.,3.,0.]])
        s=make_channel(54,[0,3],[[7],[900]])
        return [build_channel(q),build_channel(v),bytes([254])+struct.pack('<I',3),build_channel(s)]

    def test_clip_round_trip_is_byte_exact_and_keeps_shared_references(self):
        body=clip_body(self.records());clip=parse_clip(body)
        self.assertEqual(build_clip(clip),body)
        self.assertEqual(clip['tracks'][2]['shared_reference'],3)
        self.assertEqual(len(clip['tracks']),len(parse_clip_body(body)['tracks']))
        self.assertEqual(parse_clip(clip_body([]))['tracks'],[])
        self.assertEqual(build_clip(parse_clip(clip_body([]))),clip_body([]))

    def test_amplitude_scaling_changes_only_selected_track(self):
        body=clip_body(self.records());clip=parse_clip(body)
        out=scale_rotation_amplitude(clip,0,2.0);data=build_clip(out)
        self.assertEqual(len(data),len(body));parse_clip_body(data)
        again=parse_clip(data)
        for index in (1,2,3):self.assertEqual(build_track(again['tracks'][index]),build_track(clip['tracks'][index]))
        old,new=channel_values(clip['tracks'][0]),channel_values(again['tracks'][0])
        for a,b in zip(old,new):
            angle=lambda q:2*math.atan2(math.sqrt(sum(x*x for x in q[:3])),abs(q[3]))
            self.assertAlmostEqual(angle(b),2*angle(a),delta=.002)
        zero=scale_rotation_amplitude(clip,0,0)
        self.assertTrue(all(abs(v[3])>.9999 for v in channel_values(zero['tracks'][0])))

    def test_unit_factor_is_the_identity_and_bad_targets_fail(self):
        body=clip_body(self.records());clip=parse_clip(body)
        self.assertEqual(build_clip(scale_rotation_amplitude(clip,0,1)),body)
        for index in (1,2,3,4,-1):
            with self.assertRaises(ValueError):scale_rotation_amplitude(clip,index,2)
        with self.assertRaises(ValueError):scale_rotation_amplitude(clip,0,float('inf'))

    def test_restricted_z16_track_stays_restricted(self):
        ch=make_channel(21,[0,10],[unit(0,0,.1,1),unit(0,0,.5,1)])
        clip=parse_clip(clip_body([build_channel(ch)]))
        out=scale_rotation_amplitude(clip,0,3.)
        for v in channel_values(out['tracks'][0]):self.assertEqual(v[:2],[0,0])

    def test_scale_quaternion_identity_and_double_angle(self):
        self.assertEqual(scale_quaternion_rotation([0,0,0,1],5),[0,0,0,1])
        half=math.sqrt(.5);q=scale_quaternion_rotation([0,0,half,half],2)   # 90 -> 180 degrees
        self.assertAlmostEqual(abs(q[2]),1,places=9);self.assertAlmostEqual(q[3],0,places=9)


if __name__=='__main__':unittest.main()
