"""Recovered scalar dispatch-zero small-angle trig; LINK_SOLVER.md, Scalar trig."""
import math
from reference.central_impulse import f32

SMALL_ANGLE_LIMIT=float.fromhex('0x1.921fb54442d18p-1')


def small_angle_sin_cos(value):
    """Return native float32 sine/cosine for finite float32 |x| <= pi/4.

    Uses inspected binary64 polynomial evaluation, not platform libm. Larger
    arguments require the still-separate reduction paths and are rejected.
    Floating-point status flags, alternate CPU dispatch and NaNs are not modeled.
    """
    x=f32(value)
    if not math.isfinite(x) or abs(x)>SMALL_ANGLE_LIMIT:
        raise ValueError('Recovered scalar trig requires finite float32 abs(x) <= pi/4')
    square=x*x
    if abs(x)<2.0**-13:
        sine=x
    elif abs(x)<2.0**-7:
        sine=f32(x-((square*x)*float.fromhex('0x1.5555555555555p-3')))
    else:
        fourth=square*square;cube=x*square
        a=float.fromhex('0x1.71de3a556c734p-19')*square
        b=float.fromhex('0x1.1111111111111p-7')*square
        a=a+float.fromhex('-0x1.a01a01a01a01ap-13')
        a=a*fourth;b=b+float.fromhex('-0x1.5555555555555p-3')
        a=a+b;a=a*cube;sine=f32(x+a)
    fourth=square*square
    a=float.fromhex('-0x1.27e4fb7789f5cp-22')*square
    b=float.fromhex('-0x1.6c16c16c16c16p-10')*square
    c=-.5*square
    a=a+float.fromhex('0x1.a01a01a01a019p-16');a=a*fourth
    b=b+float.fromhex('0x1.5555555555555p-5');a=a+b;a=a*fourth
    c=c+1.;cosine=f32(c+a)
    return sine,cosine


def _sine_polynomial(x):
    z=x*x;fourth=z*z
    a=float.fromhex('0x1.71de3a556c734p-19')*z
    b=float.fromhex('0x1.1111111111111p-7')*z
    a=(a+float.fromhex('-0x1.a01a01a01a01ap-13'))*fourth
    b=b+float.fromhex('-0x1.5555555555555p-3')
    return x+((a+b)*(x*z))


def _cosine_polynomial(x):
    z=x*x;fourth=z*z
    a=float.fromhex('-0x1.27e4fb7789f5cp-22')*z
    b=float.fromhex('-0x1.6c16c16c16c16p-10')*z
    a=(a+float.fromhex('0x1.a01a01a01a019p-16'))*fourth
    b=b+float.fromhex('0x1.5555555555555p-5')
    return (-.5*z+1.)+((a+b)*fourth)


def scalar_sin_cos(value):
    """Recovered dispatch-zero finite range abs(float32(x)) <500000.

    Large-argument reduction and alternate dispatch remain unsupported. Uses
    binary64 split-pi/2 reduction with inspected cancellation correction.
    """
    import struct
    x=f32(value);a=abs(x)
    if not math.isfinite(x) or a>=500000.:
        raise ValueError('Recovered scalar trig requires finite float32 abs(x) <500000')
    if a<=SMALL_ANGLE_LIMIT:return small_angle_sin_cos(x)
    def exponent(v):return (struct.unpack('<Q',struct.pack('<d',v))[0]>>52)&0x7ff
    quadrant=int(a*float.fromhex('0x1.45f306dc9c883p-1')+.5)
    head=a-float.fromhex('0x1.921fb54400000p+0')*quadrant
    tail=float.fromhex('0x1.0b4611a626331p-34')*quadrant
    reduced=head-tail;reduced_exponent=exponent(reduced)
    if exponent(a)-reduced_exponent>15:
        part=float.fromhex('0x1.0b4611a600000p-34')*quadrant
        remainder=float.fromhex('0x1.3198a2e037073p-69')*quadrant
        next_head=head-part
        error=(head-next_head)-part
        reduced=next_head-(remainder-error)
    if reduced_exponent<0x3f2:
        if reduced_exponent<=0x3de:
            sine=reduced;cosine=1.
        else:
            z=reduced*reduced
            sine=reduced-((float.fromhex('0x1.5555555555555p-3')*reduced)*z)
            cosine=1.-z*.5
    else:
        sine=_sine_polynomial(reduced);cosine=_cosine_polynomial(reduced)
    sin_result=cosine if quadrant&1 else sine
    cos_result=sine if quadrant&1 else cosine
    if bool((quadrant>>1)&1)!=(x<0):sin_result=0.-sin_result
    if (quadrant+1)&2:cos_result=0.-cos_result
    return f32(sin_result),f32(cos_result)
