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
