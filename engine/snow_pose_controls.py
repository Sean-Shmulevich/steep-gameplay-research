"""Connected valid-configuration pose spring preparation.

Evidence: CENTRAL_IMPULSE.md, Connected pose spring preparation.
"""
from reference.central_impulse import f32
from .snow_pose_damping import prepare_pose_damping
from .snow_pose_frequency import prepare_pose_frequencies
from .snow_pose_springs import pose_spring_coefficients


def prepare_pose_controls(*, config_valid_byte, immersion_selector_byte,
                          primary_immersion, alternate_immersion,
                          speed_argument, depth, override, preferred_byte,
                          defaults, frequency_profiles, override_profile,
                          damping_profiles, frame_coefficients):
    """Return arrays and spring records; supplied frame coefficients stay unchanged.

    The coefficient producer belongs to an earlier phase. This function neither
    reruns it nor asserts a same-phase frame snapshot or native solver update.
    """
    for flag in (config_valid_byte,immersion_selector_byte,preferred_byte):
        if not isinstance(flag,int) or not 0<=flag<=255:raise ValueError('Raw uint8 flags required')
    if config_valid_byte==0:raise ValueError('Protected invalid configuration is unresolved')
    immersion=f32(primary_immersion if immersion_selector_byte==1 else alternate_immersion)
    ratios=prepare_pose_damping(speed_argument,immersion,damping_profiles)
    frequencies=prepare_pose_frequencies(defaults,speed_argument,immersion,depth,
                                         override,frequency_profiles,override_profile)
    if len(frame_coefficients)!=3:raise ValueError('Three frame coefficients required')
    coefficients=list(map(f32,frame_coefficients))
    if preferred_byte:coefficients[2]=f32(coefficients[2]*100.)
    springs=pose_spring_coefficients(coefficients,frequencies['frequencies'],ratios)
    return {'selected_immersion':immersion,'frequencies':frequencies['frequencies'],
            'frequency_branches':frequencies['branches'],'damping_ratios':ratios,
            'spring_coefficients':coefficients,'records':springs}
