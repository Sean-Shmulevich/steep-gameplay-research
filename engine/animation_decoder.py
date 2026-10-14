"""Recovered animation channel adapters with explicit numerical substitutes.

Evidence: docs/reconstruction/ANIMATION_QUATERNION_SAMPLER.md. No clip container,
rig identity, graph selection or physics coupling is implied by this decoder.
"""
import math
import struct
from .animation_endpoints import f32
from .animation_key_selection import select_byte_key, select_mask_key, select_wide_key
from .animation_interpolation import quaternion_sample_blend


def sample_encoding_zero(payload, time, hint, cursor=0xffffffff, *, rsqrt_estimate=None):
    """Decode supplied channel bytes, preserving separate float time and hint.

    Byte0 encoding, byte1 count, count-1 stored byte ticks; float4 samples start
    at (count+16)&~15. Bounds/finite/count checks are reconstruction safeguards.
    """
    data = memoryview(payload)
    if len(data) < 2 or data[0] != 0:
        raise ValueError('expected encoding-zero channel header')
    count = data[1]
    if count == 0:
        raise ValueError('zero-key channel has no sample payload')
    offset = (count+16) & 0xfffffff0
    if len(data) < offset+16*count:
        raise ValueError('truncated quaternion channel')
    selected = select_byte_key(count, data[2:count+1], hint, cursor)
    time = f32(time)
    if not math.isfinite(time):
        raise ValueError('expected finite sample time')
    index = selected['cursor']
    a = list(struct.unpack_from('<4f',data,offset+index*16))
    if not all(math.isfinite(v) for v in a):
        raise ValueError('nonfinite selected quaternion')
    packed = selected['packed_ticks']
    weight = None
    if packed > 65535:
        b = struct.unpack_from('<4f',data,offset+(index+1)*16)
        scale = f32(1/60)
        start, end = f32((packed & 65535)*scale), f32((packed >> 16)*scale)
        clamped = max(start,min(end,time))
        weight = f32(f32(clamped-start)/f32(end-start))
        a = quaternion_sample_blend(a,b,weight,rsqrt_estimate=rsqrt_estimate)
    return {**selected,'value':a,'weight':weight}


def encoding_zero_decoder(descriptor, payload, width, time, output, state):
    """Callback for animation_sampling.sample_channel; descriptor is encoding 0.

    Uses scalar reciprocal seed policy. Updates caller's cursor and output only
    after successful decoding; failure atomicity is an independent API safeguard.
    """
    if type(descriptor) is not int or descriptor != 0 or width != 16:
        raise ValueError('encoding-zero decoder requires descriptor 0 and width 16')
    cursor = 0xffffffff if state.cursor == -1 else state.cursor
    result = sample_encoding_zero(payload,time,state.hint,cursor)
    output[:] = result['value']
    state.cursor = result['cursor']


def sample_encoding_27(payload, time, hint, cursor=0xffffffff):
    """Decode byte-time float3 vectors into float4 with a zero fourth lane.

    Evidence: ANIMATION_VECTOR_SAMPLER.md. Uses the same key selector as encoding
    zero, four-byte sample alignment, and twelve-byte sample stride.
    """
    data = memoryview(payload)
    if len(data) < 2 or data[0] != 27:
        raise ValueError('expected encoding-27 channel header')
    count = data[1]
    if count == 0:
        raise ValueError('zero-key channel has no sample payload')
    offset = (count+4) & 0xfffffffc
    if len(data) < offset+12*count:
        raise ValueError('truncated vector channel')
    selected = select_byte_key(count,data[2:count+1],hint,cursor)
    time = f32(time)
    if not math.isfinite(time):
        raise ValueError('expected finite sample time')
    index = selected['cursor']
    value = list(struct.unpack_from('<3f',data,offset+12*index))
    if not all(math.isfinite(v) for v in value):
        raise ValueError('nonfinite selected vector')
    packed, weight = selected['packed_ticks'], None
    if packed > 65535:
        other = struct.unpack_from('<3f',data,offset+12*(index+1))
        if not all(math.isfinite(v) for v in other):
            raise ValueError('nonfinite selected vector')
        scale = f32(1/60)
        start,end = f32((packed&65535)*scale),f32((packed>>16)*scale)
        weight = f32(f32(max(start,min(end,time))-start)/f32(end-start))
        value = [f32(a+f32(weight*f32(b-a))) for a,b in zip(value,other)]
    return {**selected,'value':value+[0.0],'weight':weight}


def registered_channel_decoder(descriptor, payload, width, time, output, state):
    """Sampling callback for supported quaternion, vector and scalar encoding IDs."""
    supported=(0,9,11,12,14,21,23,24,26,27,28,29,39,54)
    if type(descriptor) is not int or descriptor not in supported:
        raise ValueError('unsupported descriptor')
    if width != (4 if descriptor in (39,54) else 16):
        raise ValueError('descriptor output width mismatch')
    cursor = 0xffffffff if state.cursor == -1 else state.cursor
    result = {0:sample_encoding_zero,9:sample_encoding_9,11:sample_encoding_11,12:sample_encoding_12,14:sample_encoding_14,21:sample_encoding_21,23:sample_encoding_23,24:sample_encoding_24,26:sample_encoding_26,29:sample_encoding_29,27:sample_encoding_27,28:sample_encoding_28,39:sample_encoding_39,54:sample_encoding_54}[descriptor](
        payload,time,state.hint,cursor)
    output[:] = result['value']
    state.cursor = result['cursor']


def unpack_serialized_channel(data, offset=0):
    """Adapt one supported serialized channel record to runtime layout.

    Disk layout: encoding:u8, opaque_allocation:u32, count:u32, count-1 time
    bytes, tightly packed samples. Encoding 14 instead uses mode and mask bytes.
    Does not parse a clip or resolve shared refs.
    Returns consumed length and opaque metadata; trailing records are permitted.
    Evidence: ANIMATION_SERIALIZED_CHANNELS.md. Rejects counts exceeding the
    runtime uint8 representation rather than truncating them.
    """
    data = memoryview(data)
    if type(offset) is not int or offset < 0 or offset+9 > len(data):
        raise ValueError('truncated serialized channel header')
    encoding = data[offset]
    if encoding not in (0,9,11,12,14,21,23,24,26,27,28,29,39,54):
        raise ValueError('unsupported serialized channel encoding')
    allocation,count = struct.unpack_from('<II',data,offset+1)
    if encoding==28:
        from .animation_channel_framing import frame_serialized_channel
        framed=frame_serialized_channel(data,offset)
        if count>65535:raise ValueError('wide count exceeds uint16 runtime range')
        header=2 if count<256 else 4
        sample_offset=(header+2*(count-1)+3)&~3
        result=bytearray(sample_offset)
        result[0]=encoding
        if header==2:result[1]=count
        else:struct.pack_into('<H',result,2,count)
        result[header:header+2*(count-1)]=data[offset+9:framed['sample_offset']]
        result.extend(data[framed['sample_offset']:offset+framed['consumed']])
        return {'encoding':encoding,'payload':bytes(result),'consumed':framed['consumed'],
                'opaque_allocation':allocation}

    if encoding in (11,14,23,26,29):
        if offset+10>len(data):raise ValueError('missing mask mode')
        mode=data[offset+9];size=mode&63
        mask=data[offset+10:offset+10+size]
        select_mask_key(mode,mask,0)
        if int.from_bytes(mask,'little').bit_count()!=count:
            raise ValueError('mask key count mismatch')
        stride,alignment={11:(4,4),14:(6,2),23:(2,2),26:(12,4),29:(12,4)}[encoding]
        end=offset+10+size+stride*count
        if end>len(data):raise ValueError('truncated masked quaternion samples')
        result=bytearray((size+1+alignment)&~(alignment-1))
        result[:2]=bytes((encoding,mode));result[2:2+size]=mask
        result.extend(data[offset+10+size:end])
        return {'encoding':encoding,'payload':bytes(result),'consumed':end-offset,
                'opaque_allocation':allocation}
    if not 1 <= count <= 255:
        raise ValueError('serialized count outside supported runtime range')
    stride,alignment = {0:(16,16),9:(4,4),12:(6,2),21:(2,2),24:(12,4),27:(12,4),39:(1,1),54:(4,4)}[encoding]
    end = offset+9+(count-1)+count*stride
    if end > len(data):
        raise ValueError('truncated serialized channel data')
    times = data[offset+9:offset+9+count-1]
    # Validate sorted byte timestamps without decoding sample components.
    select_byte_key(count,times,0)
    sample_offset = (count+alignment)&~(alignment-1)
    result = bytearray(sample_offset)
    result[:2] = bytes((encoding,count))
    result[2:count+1] = times
    result.extend(data[offset+9+count-1:end])
    return {'encoding':encoding,'payload':bytes(result),'consumed':end-offset,
            'opaque_allocation':allocation}


def quaternion_z16(word):
    """Recovered restricted xyzw quaternion; only z/w can be nonzero."""
    if type(word) is not int or not 0 <= word <= 65535:
        raise ValueError('expected uint16 quaternion word')
    value = f32(f32((word&32767)*f32(4.316100603318773e-05))-f32(.7071067690849304))
    missing = f32(math.sqrt(f32(1-f32(value*value))))
    return [0.0,0.0,missing,value] if word&32768 else [0.0,0.0,value,missing]


def sample_encoding_21(payload,time,hint,cursor=0xffffffff,*,rsqrt_estimate=None):
    """Sample byte-time packed z/w quaternion tracks; see packed sampler guide."""
    data=memoryview(payload)
    if len(data)<2 or data[0]!=21:
        raise ValueError('expected encoding-21 channel header')
    count=data[1]
    if count==0:
        raise ValueError('zero-key channel has no sample payload')
    offset=(count+2)&0xfffffffe
    if len(data)<offset+2*count:
        raise ValueError('truncated packed quaternion channel')
    selected=select_byte_key(count,data[2:count+1],hint,cursor)
    time=f32(time)
    if not math.isfinite(time):raise ValueError('expected finite sample time')
    index=selected['cursor']
    value=quaternion_z16(struct.unpack_from('<H',data,offset+2*index)[0])
    packed,weight=selected['packed_ticks'],None
    if packed>65535:
        other=quaternion_z16(struct.unpack_from('<H',data,offset+2*(index+1))[0])
        scale=f32(1/60)
        start,end=f32((packed&65535)*scale),f32((packed>>16)*scale)
        weight=f32(f32(max(start,min(end,time))-start)/f32(end-start))
        value=quaternion_sample_blend(value,other,weight,rsqrt_estimate=rsqrt_estimate)
    return {**selected,'value':value,'weight':weight}


def quaternion_smallest_three32(word, *, rsqrt_estimate=None):
    """Recovered ten-bit fields and omitted-lane reconstruction.

    Scalar reciprocal seed is a substitute for RSQRTPS. Invalid/nonpositive
    radicands are rejected by this API, rather than producing native NaNs.
    """
    if type(word) is not int or not 0 <= word <= 0xffffffff:
        raise ValueError('expected uint32 quaternion word')
    values=[f32(f32(((word>>shift)&1023)*f32(.0013837706064805388))
                +f32(-.7071067690849304)) for shift in (20,10,0)]
    squares=[f32(v*v) for v in values]
    radicand=f32(1-f32(squares[0]+f32(squares[1]+squares[2])))
    if not math.isfinite(radicand) or radicand<=0:
        raise ValueError('expected positive omitted-component radicand')
    seed=f32(1/math.sqrt(radicand) if rsqrt_estimate is None else rsqrt_estimate)
    if not math.isfinite(seed) or seed<=0:
        raise ValueError('expected positive finite reciprocal seed')
    correction=f32(f32(3-f32(f32(seed*radicand)*seed))*f32(.5*seed))
    values.insert(word>>30,f32(radicand*correction))
    return values


def _sample_general_packed(payload,time,hint,cursor,encoding,rsqrt_estimate):
    """Sample byte-time general quaternion tracks with scalar value-decode seeds.

    rsqrt_estimate applies to interpolation normalization only. Direct packed
    word decoding accepts its own estimate through quaternion_smallest_three32.
    """
    data=memoryview(payload)
    if len(data)<2 or data[0]!=encoding:
        raise ValueError('unexpected packed quaternion channel header')
    count=data[1]
    if count==0:raise ValueError('zero-key channel has no sample payload')
    stride,alignment={9:(4,4),12:(6,2),24:(12,4)}[encoding]
    offset=(count+alignment)&~(alignment-1)
    if len(data)<offset+stride*count:raise ValueError('truncated quaternion channel')
    selected=select_byte_key(count,data[2:count+1],hint,cursor)
    time=f32(time)
    if not math.isfinite(time):raise ValueError('expected finite sample time')
    index=selected['cursor']
    def decode(index):
        if encoding==9:
            return quaternion_smallest_three32(struct.unpack_from('<I',data,offset+stride*index)[0])
        if encoding==24:
            return quaternion_three_floats(struct.unpack_from('<3I',data,offset+stride*index))
        return quaternion_smallest_three48(struct.unpack_from('<3H',data,offset+stride*index))
    value=decode(index)
    packed,weight=selected['packed_ticks'],None
    if packed>65535:
        other=decode(index+1)
        scale=f32(1/60)
        start,end=f32((packed&65535)*scale),f32((packed>>16)*scale)
        weight=f32(f32(max(start,min(end,time))-start)/f32(end-start))
        value=quaternion_sample_blend(value,other,weight,rsqrt_estimate=rsqrt_estimate)
    return {**selected,'value':value,'weight':weight}


def quaternion_smallest_three48(words, *, rsqrt_estimate=None):
    """Three uint16 words, fifteen-bit components, selector in first two high bits."""
    words=tuple(words)
    if len(words)!=3 or any(type(w) is not int or not 0<=w<=65535 for w in words):
        raise ValueError('expected three uint16 quaternion words')
    values=[f32(f32((w&32767)*f32(4.316100603318773e-05))+f32(-.7071067690849304)) for w in words]
    squares=[f32(v*v) for v in values]
    n=f32(1-f32(squares[0]+f32(squares[1]+squares[2])))
    if not math.isfinite(n) or n<=0:raise ValueError('expected positive omitted-component radicand')
    r=f32(1/math.sqrt(n) if rsqrt_estimate is None else rsqrt_estimate)
    if not math.isfinite(r) or r<=0:raise ValueError('expected positive finite reciprocal seed')
    missing=f32(n*f32(f32(3-f32(f32(r*n)*r))*f32(.5*r)))
    values.insert((words[0]>>15)|((words[1]>>15)<<1),missing)
    return values


def sample_encoding_9(payload,time,hint,cursor=0xffffffff,*,rsqrt_estimate=None):
    return _sample_general_packed(payload,time,hint,cursor,9,rsqrt_estimate)


def sample_encoding_12(payload,time,hint,cursor=0xffffffff,*,rsqrt_estimate=None):
    return _sample_general_packed(payload,time,hint,cursor,12,rsqrt_estimate)


def _sample_mask_channel(payload,time,hint,cursor,encoding,rsqrt_estimate):
    """Sample supported mask-time channels; incoming cursor is intentionally unused."""
    data=memoryview(payload)
    if len(data)<2 or data[0]!=encoding:raise ValueError('unexpected mask quaternion header')
    mode=data[1];size=mode&63;mask=data[2:2+size]
    selected=select_mask_key(mode,mask,hint)
    count=int.from_bytes(mask,'little').bit_count()
    stride,alignment={11:(4,4),14:(6,2),23:(2,2),26:(12,4),29:(12,4)}[encoding]
    offset=(size+1+alignment)&~(alignment-1)
    if len(data)<offset+stride*count:raise ValueError('truncated masked quaternion samples')
    time=f32(time)
    if not math.isfinite(time):raise ValueError('expected finite sample time')
    index=selected['cursor']
    def decode(index):
        if encoding==11:
            return quaternion_smallest_three32(struct.unpack_from('<I',data,offset+stride*index)[0])
        if encoding==14:
            return quaternion_smallest_three48(struct.unpack_from('<3H',data,offset+stride*index))
        if encoding==26:
            return quaternion_three_floats(struct.unpack_from('<3I',data,offset+stride*index))
        if encoding==29:
            values=list(struct.unpack_from('<3f',data,offset+stride*index))
            if not all(math.isfinite(v) for v in values):raise ValueError('nonfinite vector sample')
            return values+[0.0]
        return quaternion_z16(struct.unpack_from('<H',data,offset+stride*index)[0])
    value=decode(index)
    packed,weight=selected['packed_ticks'],None
    if packed>65535:
        other=decode(index+1)
        scale=f32(1/60)
        start,end=f32((packed&65535)*scale),f32((packed>>16)*scale)
        weight=f32(f32(max(start,min(end,time))-start)/f32(end-start))
        if encoding==29:
            value=[f32(a+f32(weight*f32(b-a))) for a,b in zip(value[:3],other[:3])]+[0.0]
        else:
            value=quaternion_sample_blend(value,other,weight,rsqrt_estimate=rsqrt_estimate)
    return {**selected,'value':value,'weight':weight}


def sample_encoding_14(payload,time,hint,cursor=0xffffffff,*,rsqrt_estimate=None):
    return _sample_mask_channel(payload,time,hint,cursor,14,rsqrt_estimate)


def sample_encoding_23(payload,time,hint,cursor=0xffffffff,*,rsqrt_estimate=None):
    return _sample_mask_channel(payload,time,hint,cursor,23,rsqrt_estimate)


def sample_encoding_11(payload,time,hint,cursor=0xffffffff,*,rsqrt_estimate=None):
    return _sample_mask_channel(payload,time,hint,cursor,11,rsqrt_estimate)


def quaternion_three_floats(words, *, rsqrt_estimate=None):
    """Encoding 24: float bits retain the two embedded selector bits.

    Evidence: ANIMATION_THREE_FLOAT_SAMPLER.md. Scalar reciprocal seed and
    malformed-input rejection are reconstruction policies, not native parity.
    """
    words=tuple(words)
    if len(words)!=3 or any(type(w) is not int or not 0<=w<=0xffffffff for w in words):
        raise ValueError('expected three uint32 quaternion words')
    values=list(struct.unpack('<3f',struct.pack('<3I',*words)))
    if not all(math.isfinite(v) for v in values):
        raise ValueError('expected finite quaternion components')
    squares=[f32(v*v) for v in values]
    n=f32(1-f32(squares[0]+f32(squares[1]+squares[2])))
    if not math.isfinite(n) or n<=0:
        raise ValueError('expected positive omitted-component radicand')
    r=f32(1/math.sqrt(n) if rsqrt_estimate is None else rsqrt_estimate)
    if not math.isfinite(r) or r<=0:
        raise ValueError('expected positive finite reciprocal seed')
    missing=f32(n*f32(f32(3-f32(f32(n*r)*r))*f32(.5*r)))
    values.insert((words[0]&1)|((words[1]&1)<<1),missing)
    return values


def sample_encoding_24(payload,time,hint,cursor=0xffffffff,*,rsqrt_estimate=None):
    return _sample_general_packed(payload,time,hint,cursor,24,rsqrt_estimate)


def _sample_scalar(payload,time,hint,cursor,encoding):
    """Recovered scalar byte-time paths; see ANIMATION_SCALAR_SAMPLERS.md."""
    data=memoryview(payload)
    if len(data)<2 or data[0]!=encoding:raise ValueError('unexpected scalar channel header')
    count=data[1]
    if not count:raise ValueError('zero-key channel has no sample payload')
    stride=1 if encoding==39 else 4
    offset=(count+stride)&~(stride-1)
    if len(data)<offset+stride*count:raise ValueError('truncated scalar channel')
    selected=select_byte_key(count,data[2:count+1],hint,cursor)
    time=f32(time)
    if not math.isfinite(time):raise ValueError('expected finite sample time')
    def decode(index):
        if encoding==39:
            return f32(struct.unpack_from('<b',data,offset+index)[0]*f32(.008))
        return struct.unpack_from('<I',data,offset+4*index)[0]
    value=decode(selected['cursor']);packed=selected['packed_ticks'];weight=None
    if packed>65535:
        other=decode(selected['cursor']+1)
        scale=f32(1/60)
        start,end=f32((packed&65535)*scale),f32((packed>>16)*scale)
        weight=f32(f32(max(start,min(end,time))-start)/f32(end-start))
        if encoding==39:
            value=f32(value+f32(weight*f32(other-value)))
        else:
            difference=f32((other-value)&0xffffffff)
            increment=math.trunc(f32(f32(weight*difference)+f32(.5)))
            value=(value+increment)&0xffffffff
    return {**selected,'value':[value],'weight':weight}


def sample_encoding_39(payload,time,hint,cursor=0xffffffff):
    return _sample_scalar(payload,time,hint,cursor,39)


def sample_encoding_54(payload,time,hint,cursor=0xffffffff):
    return _sample_scalar(payload,time,hint,cursor,54)


def sample_encoding_26(payload,time,hint,cursor=0xffffffff,*,rsqrt_estimate=None):
    return _sample_mask_channel(payload,time,hint,cursor,26,rsqrt_estimate)


def sample_encoding_29(payload,time,hint,cursor=0xffffffff):
    return _sample_mask_channel(payload,time,hint,cursor,29,None)


def wide_channel_layout(payload):
    """Read native short/extended count header and stored uint16 timestamps."""
    data=memoryview(payload)
    if len(data)<2:raise ValueError('truncated wide header')
    count=data[1];header=2
    if count==0:
        if len(data)<4:raise ValueError('truncated extended wide count')
        count=struct.unpack_from('<H',data,2)[0];header=4
    if count==0:raise ValueError('zero-key wide channel')
    end=header+2*(count-1)
    if len(data)<end:raise ValueError('truncated wide times')
    ticks=struct.unpack_from('<'+'H'*(count-1),data,header)
    return count,ticks,end


def sample_encoding_28(payload,time,hint,cursor=0xffffffff):
    """Recovered wide-time float3 vector sampling; see ANIMATION_WIDE_TIMES.md."""
    data=memoryview(payload)
    if not data or data[0]!=28:raise ValueError('expected encoding-28 channel')
    count,ticks,end=wide_channel_layout(data)
    offset=(end+3)&~3
    if len(data)<offset+12*count:raise ValueError('truncated wide vector samples')
    selected=select_wide_key(count,ticks,hint,cursor)
    time=f32(time)
    if not math.isfinite(time):raise ValueError('expected finite sample time')
    def decode(index):
        value=list(struct.unpack_from('<3f',data,offset+12*index))
        if not all(math.isfinite(v) for v in value):raise ValueError('nonfinite vector sample')
        return value
    value=decode(selected['cursor']);packed=selected['packed_ticks'];weight=None
    if packed>65535:
        other=decode(selected['cursor']+1)
        scale=f32(1/60)
        start,end=f32((packed&65535)*scale),f32((packed>>16)*scale)
        weight=f32(f32(max(start,min(end,time))-start)/f32(end-start))
        value=[f32(a+f32(weight*f32(b-a))) for a,b in zip(value,other)]
    return {**selected,'value':value+[0.0],'weight':weight}
