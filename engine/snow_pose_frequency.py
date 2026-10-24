"""Recovered pose-frequency profile selection and depth override.

Evidence: CENTRAL_IMPULSE.md, Pose frequency preparation.
"""
import math
from reference.central_impulse import f32
from reference.runtime_curve import evaluate


def prepare_pose_frequencies(defaults, speed_argument, selected_immersion,
                             depth, override, profiles, override_profile):
    """Return XYZ frequencies from valid resolved profile data.

    Defaults are supplied global initializer values, not assumed zeros. Native
    profile validity gates and exceptional arithmetic are outside this API.
    """
    if len(defaults)!=3 or len(profiles)!=3:raise ValueError('Three axes required')
    result=list(map(f32,defaults))
    speed,immersion,depth,override=map(f32,(speed_argument,selected_immersion,depth,override))
    if not all(math.isfinite(x) for x in result+[speed,immersion,depth,override]):
        raise ValueError('Finite inputs required')
    branches=['default']*3
    def ordinary(index):
        profile=profiles[index];scale=f32(profile['scale'])
        if not math.isfinite(scale):raise ValueError('Finite profile scale required')
        if scale<=0:return
        speed_gain=evaluate(speed,**profile['speed_curve'])
        immersion_gain=evaluate(immersion,**profile['immersion_curve'])
        if index==0 and depth<=f32(.03):
            result[index]=20.;branches[index]='shallow'
        else:
            result[index]=f32(f32(speed_gain*scale)*immersion_gain)
            branches[index]='profile'
    ordinary(1)
    if override>0 and f32(override_profile['scale'])>0:
        result[2]=f32(evaluate(override,**override_profile['curve'])*f32(override_profile['scale']))
        branches[2]='override'
    else:ordinary(2)
    ordinary(0)
    if not all(math.isfinite(x) for x in result):raise ValueError('Finite frequencies required')
    return {'frequencies':result,'branches':branches}
