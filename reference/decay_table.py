"""Recovered 256-segment decay table builder with externally supplied samples.

CENTRAL_IMPULSE.md, 'Decay lookup construction'. Exponential implementations are
not reproduced; caller labels provenance of 257 samples. No game payloads.
"""
from reference.central_impulse import f32
from reference.runtime_curve import evaluate


def sample_arguments(low=-10., high=0.):
    low,high=map(f32,(low,high));width=f32(high-low)
    if width<=0: raise ValueError('Ascending finite bounds required')
    step=f32(width*f32(1/256))
    return tuple(f32(f32(f32(i)*step)+low) for i in range(257))


def build(samples, *, low=-10., high=0., padding=.0001):
    if len(samples)!=257: raise ValueError('Exactly 257 supplied samples required')
    low,high,padding=map(f32,(low,high,padding));width=f32(high-low)
    if width<=0 or padding<0: raise ValueError('Ascending bounds and nonnegative padding required')
    values=tuple(map(f32,samples));step=f32(width*f32(1/256))
    start=f32(low-f32(width*padding))
    segments=[]
    for i in range(256):
        slope=f32(f32(values[i+1]-values[i])/step)
        x=f32(f32(f32(i)*step)+low)
        intercept=f32(values[i]-f32(x*slope))
        segments.append((slope,intercept))
    denominator=f32(f32(f32(padding+f32(1))*width)+f32(low-start))
    return {'start':start,'index_scale':f32(f32(256)/denominator),'segments':tuple(segments)}
