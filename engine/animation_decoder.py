"""Verified encoding-zero float4 quaternion channel adapter.

Evidence: docs/reconstruction/ANIMATION_QUATERNION_SAMPLER.md. No clip container,
rig identity, graph selection or physics coupling is implied by this decoder.
"""
import math
import struct
from .animation_endpoints import f32
from .animation_key_selection import select_byte_key
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
    """Sampling callback for verified encoding IDs 0, 21 and 27 only."""
    if type(descriptor) is not int or descriptor not in (0,21,27) or width != 16:
        raise ValueError('supported descriptors are 0, 21 and 27 with width 16')
    cursor = 0xffffffff if state.cursor == -1 else state.cursor
    result = {0:sample_encoding_zero,21:sample_encoding_21,27:sample_encoding_27}[descriptor](
        payload,time,state.hint,cursor)
    output[:] = result['value']
    state.cursor = result['cursor']


def unpack_serialized_channel(data, offset=0):
    """Adapt one serialized byte-time encoding 0/21/27 record to runtime layout.

    Disk layout: encoding:u8, opaque_allocation:u32, count:u32, count-1 time
    bytes, tightly packed samples. Does not parse a clip or resolve shared refs.
    Returns consumed length and opaque metadata; trailing records are permitted.
    Evidence: ANIMATION_SERIALIZED_CHANNELS.md. Rejects counts exceeding the
    runtime uint8 representation rather than truncating them.
    """
    data = memoryview(data)
    if type(offset) is not int or offset < 0 or offset+9 > len(data):
        raise ValueError('truncated serialized channel header')
    encoding = data[offset]
    if encoding not in (0,21,27):
        raise ValueError('unsupported serialized channel encoding')
    allocation,count = struct.unpack_from('<II',data,offset+1)
    if not 1 <= count <= 255:
        raise ValueError('serialized count outside supported runtime range')
    stride,alignment = {0:(16,16),21:(2,2),27:(12,4)}[encoding]
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
