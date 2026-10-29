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
