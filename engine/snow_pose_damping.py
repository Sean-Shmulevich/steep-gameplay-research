"""Recovered profile-driven damping-ratio preparation for pose springs.

Evidence: CENTRAL_IMPULSE.md, Pose damping-ratio profiles.
"""
import math
from reference.central_impulse import f32
from reference.runtime_curve import evaluate


def prepare_pose_damping(speed_argument, selected_immersion, profiles):
    """Return ratios in XYZ order, evaluating Y,Z,X with supplied compiled curves.

    Each profile supplies scale, speed_curve, immersion_curve. Native valid-field
    gates are a caller precondition; invalid protected paths are not emulated.
    """
    if len(profiles)!=3:raise ValueError('Three axis profiles required')
    speed,immersion=f32(speed_argument),f32(selected_immersion)
    if not all(math.isfinite(x) for x in (speed,immersion)):
        raise ValueError('Finite curve arguments required')
    result=[None,None,None]
    for index in (1,2,0):
        profile=profiles[index]
        speed_gain=evaluate(speed,**profile['speed_curve'])
        immersion_gain=evaluate(immersion,**profile['immersion_curve'])
        scale=f32(profile['scale'])
        value=f32(f32(speed_gain*scale)*immersion_gain)
        if not math.isfinite(value):raise ValueError('Finite ratio required')
        result[index]=value
    return result
