"""Recovered paired-profile scalar combination and row response coefficients.

Evidence: CENTRAL_IMPULSE.md, Link profile combination and response gate.
"""
import math
from reference.central_impulse import f32

THRESHOLD=f32(1e12)


def combine_link_scalar(first,second,mode):
    """Raw modes0..5: min, max, sum, product, mean, sqrt(product).

    Finite inputs; negative geometric-mean product is outside this API domain.
    Preserve rounded subtraction and operand choice on ties, including signed zero.
    """
    if type(mode) is not int or not 0<=mode<=0xffffffff:raise ValueError('Raw uint32 mode required')
    a,b=f32(first),f32(second)
    if not math.isfinite(a) or not math.isfinite(b):raise ValueError('Finite profile values required')
    if mode==0:return a if f32(b-a)>=0 else b
    if mode==1:return b if f32(b-a)>=0 else a
    if mode==2:return f32(a+b)
    if mode==3:return f32(a*b)
    if mode==4:return f32(f32(a+b)*0.5)
    if mode==5:
        product=f32(a*b)
        if product<0:raise ValueError('Nonnegative geometric-mean product required')
        return f32(math.sqrt(product))
    return 0.0


def link_response_coefficients(first,second,modes,*,context_scalar,default_factor,context_flags):
    """Profiles/modes keyed by field30,field40,field60,field64.

    Field64 combination is evaluated only below the field60 threshold. Physical
    names and the context scalar's units remain unresolved. No singular fallback.
    """
    s=f32(context_scalar);factor=f32(default_factor)
    if not math.isfinite(s) or not math.isfinite(factor):raise ValueError('Finite context values required')
    if type(context_flags) is not int or not 0<=context_flags<=0xffffffff:raise ValueError('Raw uint32 flags required')
    def combine(name):return combine_link_scalar(first[name],second[name],modes[name])
    a=combine('field30');b=combine('field40');k=combine('field60')
    response=-f32(s*factor);gate=0.0;c=None;scaled=None
    if k<THRESHOLD:
        scaled=f32(f32((context_flags>>2)&0x3fff)*s)
        c=combine('field64');denominator=f32(f32(c*scaled)+k)
        if denominator==0 or not math.isfinite(denominator):raise ValueError('Finite nonsingular response denominator required')
        ratio=f32(s/denominator)
        response=-f32(ratio*k);gate=f32(ratio*scaled)
    return dict(combined30=a,combined40=b,combined60=k,combined64=c,
                scaled_count=scaled,response=response,seed_gate=gate)
