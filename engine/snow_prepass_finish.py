"""Recovered prepass final rotations, cross rebuild and captured-frame override.

Evidence: CENTRAL_IMPULSE.md, Final prepass basis construction.
"""
import math
from reference.central_impulse import f32
from .snow_post_pending import four
from .snow_basis_override import _cross, _normalize
from .snow_axis_rotation import rotate_basis_axis


def finish_prepass_basis(axis0, auxiliary_direction, direct_angle, curve_angle,
                         speed_argument, immersion_argument, replace_basis,
                         captured_basis, speed_curve, immersion_curve,
                         sine, cosine, reciprocal_sqrt_seed):
    """Compute even when replacement is selected; return detached basis.

    replace_basis is the previously captured comparison, not recomputed from the
    curve's selected immersion argument. Finite nonsingular geometry only.
    """
    if not isinstance(replace_basis,bool):
        raise ValueError('Explicit replacement decision required')
    a, direction=four(axis0),four(auxiliary_direction)
    third=_cross(a,direction)
    a=rotate_basis_axis(a,third,direct_angle,f32(1e-5),sine,cosine)
    speed=f32(speed_curve(f32(speed_argument)))
    angle=f32(speed*f32(curve_angle))
    immersion=f32(immersion_curve(f32(immersion_argument)))
    angle=f32(angle*immersion)
    if not math.isfinite(angle):raise ValueError('Finite composed angle required')
    third=rotate_basis_axis(third,a,angle,f32(1e-5),sine,cosine)
    second=_normalize(_cross(third,a),reciprocal_sqrt_seed)
    first=_normalize(_cross(second,third),reciprocal_sqrt_seed)
    computed=[first,second,third]
    if replace_basis:
        if len(captured_basis)!=3:raise ValueError('Three captured vectors required')
        basis=[four(v) for v in captured_basis]
    else:
        basis=[v[:] for v in computed]
    return {'basis':basis,'computed_basis':computed,'replaced':replace_basis,
            'curve_angle':angle}
