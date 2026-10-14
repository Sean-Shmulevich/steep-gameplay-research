"""Encoding-zero quaternion interpolation, over caller-supplied samples.

Evidence: docs/reconstruction/ANIMATION_QUATERNION_SAMPLER.md. This implements
blend arithmetic only, not key decoding or time-to-weight conversion.
"""
import math
from reference.animation_blending import F, add, sub, mul, POLY_SCALE, POLY_CURVATURE


def quaternion_sample_blend(start, end, weight, *, rsqrt_estimate=None):
    a, b, t = list(map(F, start)), list(map(F, end)), F(weight)
    if len(a) != 4 or len(b) != 4 or not all(math.isfinite(v) for v in a+b+[t]):
        raise ValueError('expected finite float4 samples and weight')
    if not 0 <= t <= 1:
        raise ValueError('expected clamped sample weight')
    def dot(x, y):
        products = [mul(i,j) for i,j in zip(x,y)]
        return add(add(products[1],products[3]), add(products[0],products[2]))
    d = dot(a,b)
    if abs(sub(abs(d),1)) <= F(2**-23):
        return a
    if d < F(.9893559813499451):
        if d < 0:
            b = [-v for v in b]
        aligned_dot = dot(a,b)
        k0 = sub(1,mul(POLY_SCALE,aligned_dot))
        k = mul(mul(k0,k0),POLY_CURVATURE)
        def low(u):
            # Native computes ((2u-3)*(u*k)+(k+1))*u.
            return mul(add(mul(sub(add(u,u),3),mul(u,k)),add(k,1)),u)
        corrected = low(t) if t <= .5 else sub(1,low(sub(1,t)))
        if aligned_dot < 0:
            b = [-v for v in b]
        result = [add(x,mul(corrected,sub(y,x))) for x,y in zip(a,b)]
    else:
        result = [add(mul(x,sub(1,t)),mul(y,t)) for x,y in zip(a,b)]
    norm = dot(result,result)
    if not math.isfinite(norm) or norm <= 0:
        raise ValueError('expected nonzero finite interpolated norm')
    seed = F(1/math.sqrt(norm) if rsqrt_estimate is None else rsqrt_estimate)
    if not math.isfinite(seed) or seed <= 0:
        raise ValueError('expected positive finite reciprocal seed')
    scale = mul(sub(3,mul(mul(seed,norm),seed)),mul(seed,.5))
    return [mul(v,scale) for v in result]
