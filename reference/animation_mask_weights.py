"""Recovered keyed weight walk for regular masked channel blending.

Evidence: CENTRAL_IMPULSE.md, Masked channel weight selection.
Generator reads weight bytes lazily so a consumer can perform each channel write
before the next weight read. Descriptors are stable metadata in this adapter.
"""
import math
from reference.central_impulse import f32


def iter_masked_channel_weights(descriptors, read_byte, weight, weight_mode):
    if weight_mode not in (0,1):
        raise ValueError('masked weight mode zero or one required')
    previous=0xffffffff
    effective=f32(weight_mode)
    weight=f32(weight)
    i=0
    while i<len(descriptors):
        d=descriptors[i];key=d['key']&0xffffffff;paired=False
        if key!=previous:
            effective=f32(weight_mode)
            if i+1<len(descriptors):
                following=descriptors[i+1]
                if following['key']&0xffffffff==key and following['kind']&15==0:
                    value=read_byte(following['offset'])
                    if type(value) is not int or not 0<=value<=255:
                        raise ValueError('uint8 weight channel required')
                    effective=f32(f32(f32(value)*f32(1/255))*weight)
                    paired=True
            previous=key
        scaled=f32(effective*255)
        if not math.isfinite(scaled) or not -(2**63)<=scaled<2**63:
            raise ValueError('weight conversion outside supported integer range')
        yield dict(index=i,weight=effective,integer_weight=math.trunc(scaled)&0xffffffff,
                   consumes_next=paired)
        i+=2 if paired else 1
