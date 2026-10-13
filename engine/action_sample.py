"""Recovered local two-axis action publication, without device/clock inference.

Evidence: docs/reconstruction/ACTION_RESET_CALLBACK.md. Caller supplies boolean
query outcomes and optional processed vector. No player binding or processor is
inferred. Native rsqrt estimate may be supplied; default sqrt reciprocal is a
labeled derived substitute, not bit-exact SIMD emulation.
"""
import math
import struct


def f32(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('Expected finite numeric action value')
    try:result=struct.unpack('<f',struct.pack('<f',value))[0]
    except OverflowError as exc:raise ValueError('Action value exceeds float32') from exc
    if not math.isfinite(result):raise ValueError('Action operation exceeds finite float32')
    return result


def combine_directions(*,negative_x,positive_x,positive_y,negative_y):
    """Each direction is a pair of boolean query outcomes, combined by OR."""
    directions=[]
    for pair in (negative_x,positive_x,positive_y,negative_y):
        if not isinstance(pair,(list,tuple)) or len(pair)!=2 or any(type(v) is not bool for v in pair):
            raise ValueError('Each direction requires two explicit booleans')
        directions.append(any(pair))
    nx,px,py,ny=directions
    return [float(px)-float(nx),float(py)-float(ny),0.,0.]


def publish_vector(vector,*,rsqrt_estimate=None):
    """Describe sampled, direction, magnitude and status fields for this subtype.

    vector is the already processed four-lane sample, not assumed unit length.
    Float32 sum order is (xx+zz)+(yy+ww). Preserve small vectors unchanged.
    This pure kernel neither publishes to another thread nor creates a generation.
    """
    if not isinstance(vector,(list,tuple)) or len(vector)!=4:raise ValueError('Expected four sample lanes')
    v=[f32(x) for x in vector];xx,yy,zz,ww=[f32(x*x) for x in v]
    n=f32(f32(xx+zz)+f32(yy+ww));magnitude=f32(math.sqrt(n))
    if abs(n)<=f32(9.999999439624929e-11):
        direction=list(v);policy='recovered_small_vector_retention'
    else:
        if rsqrt_estimate is None:
            r=f32(1/math.sqrt(n));policy='derived_scalar_reciprocal_seed_with_recovered_refinement'
        else:
            r=f32(rsqrt_estimate)
            if r<=0:raise ValueError('Positive reciprocal sqrt seed required')
            policy='caller_supplied_reciprocal_seed_with_recovered_refinement'
        correction=f32(3-f32(f32(r*n)*r))
        factor=f32(correction*f32(.5*r))
        direction=[f32(x*factor) for x in v]
    return {'sampled_vector':v,'direction':direction,'magnitude':magnitude,
            'status':abs(magnitude)>f32(9.999999747378752e-6),
            'squared_length':n,'normalization_policy':policy,
            'sample_generation_established':False}
