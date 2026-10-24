"""Recovered signed-input gain for the prepass projection direction.

Evidence: CENTRAL_IMPULSE.md, Signed prepass direction gain.
"""
import math
from reference.central_impulse import f32


def prepass_direction_gain(control, special_byte, speed_argument,
                           control_curve, speed_curve):
    """Return gain with explicit native curve services, preserving call order.

    Called only below the earlier normal-Z threshold. This routine supplies no
    control units, runtime reads, curve payloads or angular interpretation.
    """
    if not isinstance(special_byte,int) or not 0 <= special_byte <= 255:
        raise ValueError('Raw uint8 special flag required')
    def scalar(x):
        x=f32(x)
        if not math.isfinite(x):raise ValueError('Finite scalar required')
        return x
    x=scalar(control)
    origin=scalar(control_curve(0.))
    if special_byte and x <= 0:
        if x < -.5:
            gain=1.
        else:
            gain=f32(f32(f32(x+x)*f32(origin-1.))+origin)
    else:
        gain=scalar(control_curve(x if special_byte else abs(x)))
    if special_byte:
        multiplier=1. if x < -.5 else scalar(speed_curve(scalar(speed_argument)))
        gain=f32(gain*multiplier)
    return gain
