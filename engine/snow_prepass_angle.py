"""Recovered optional prepass rotation angle and its gate-state publication.

Evidence: CENTRAL_IMPULSE.md, Control-dependent prepass angle.
Inputs are resolved scalar fields, not inferred control names or live pointers.
"""
import math
from reference.central_impulse import f32


def control_prepass_angle(*, mode_byte, inhibit_byte, candidate_byte,
                          preferred_byte, suppress_byte, retention_byte,
                          prior_gate_byte, control_a, control_b, sign_gain,
                          override, drive, base_angle, added_angle,
                          candidate_gain, speed_argument, immersion_argument,
                          speed_curve, immersion_curve):
    """Return optional radians and next gate byte; do not rotate a basis here.

    Curve services run only on the angle path, speed first. Validation and
    detached diagnostics are authored interfaces. Native producer units remain
    unresolved except that the resulting angle enters a radian rotation helper.
    """
    for flag in (mode_byte,inhibit_byte,candidate_byte,preferred_byte,
                 suppress_byte,retention_byte,prior_gate_byte):
        if not isinstance(flag,int) or not 0 <= flag <= 255:
            raise ValueError('Raw uint8 flags required')
    result={'angle':None,'gate_byte':prior_gate_byte,'gate_written':False}
    if mode_byte != 1 or inhibit_byte != 0:
        return result
    def scalar(value):
        value=f32(value)
        if not math.isfinite(value):raise ValueError('Finite scalar required')
        return value
    candidate=False
    if candidate_byte:
        a,b=scalar(control_a),scalar(control_b)
        candidate=(abs(a)>.5 and abs(b)>.5 and
                   f32(a*scalar(sign_gain))>0 and scalar(override)<=0 and
                   suppress_byte==0)
    result.update(gate_byte=int(candidate and preferred_byte==0),gate_written=True)
    if preferred_byte:
        return result
    speed=scalar(speed_curve(scalar(speed_argument)))
    immersion=scalar(immersion_curve(scalar(immersion_argument)))
    base,added=scalar(base_angle),scalar(added_angle)
    if retention_byte:
        angle=f32(base+added)
    else:
        angle=f32(f32(scalar(drive)+1.)*added)
        angle=f32(angle*(scalar(candidate_gain) if candidate else 1.))
        angle=f32(angle+(0. if candidate else base))
    angle=f32(angle*speed)
    angle=f32(angle*immersion)
    result['angle']=-angle
    return result
