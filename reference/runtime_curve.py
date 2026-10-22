"""Recovered compiled slope/intercept curve evaluation for finite inputs.

See docs/reconstruction/CENTRAL_IMPULSE.md#compiled-curve-evaluation.
Evaluates runtime tables and builds them from caller-supplied uniform samples.
Asset decoding and live profile selection are outside this module.
"""
import math
from reference.central_impulse import f32


def evaluate(value, start, index_scale, segments):
    """Return the original finite-domain clamp/index/multiply/add sequence.

    Positive scale, valid segments and representable index are authored API
    validation. Native malformed-table and exceptional-float behavior is excluded.
    """
    value, start, index_scale = map(f32, (value, start, index_scale))
    if index_scale <= 0 or not segments or len(segments) >= 1 << 24:
        raise ValueError('positive scale and a nonempty bounded table required')
    position = f32(f32(value-start)*index_scale)
    if position < 0:
        index, sample = 0, start
    else:
        if position >= 1 << 31:
            raise ValueError('native integer conversion range exceeded')
        index, sample = math.floor(position), value
        if index >= len(segments):
            index = len(segments)-1
            sample = f32(f32(f32(len(segments))/index_scale)+start)
    slope, intercept = map(f32, segments[index])
    return f32(f32(sample*slope)+intercept)


def compile_samples(domain, samples, *, zero_origin=False):
    """Recovered uniform-sample table builder, including padding and float32 order.

    zero_origin exposes the native flag: start=0 and one padding width. Its
    semantic caller role is not assigned. Ordinary curves use low-epsilon and
    two padding widths. Finite ascending domain/at least two samples are our
    API requirements; original allocation and invalid-input paths are excluded.
    """
    if len(domain) != 2 or len(samples) < 2 or len(samples) >= 1 << 24 or type(zero_origin) is not bool:
        raise ValueError('two domain bounds, at least two samples and boolean mode required')
    low,high = map(f32,domain)
    values = tuple(map(f32,samples))
    width = f32(high-low)
    if width <= 0:
        raise ValueError('ascending finite domain required')
    count = len(values)-1
    step = f32(width/f32(count))
    segments=[]
    for i in range(count):
        slope=f32(f32(values[i+1]-values[i])/step)
        x=f32(f32(f32(i)*step)+low)
        intercept=f32(values[i]-f32(x*slope))
        segments.append((slope,intercept))
    epsilon=min(f32(.0001),f32(width*f32(.0001)))
    padded_width=f32(f32((1. if zero_origin else 2.)*epsilon)+width)
    return {'start':0. if zero_origin else f32(low-epsilon),
            'index_scale':f32(f32(count)/padded_width),'segments':tuple(segments)}
