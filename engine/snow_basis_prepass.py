"""Connected finite-domain snow basis prepass with explicit runtime inputs.

Evidence: CENTRAL_IMPULSE.md, Connected basis prepass.
Only the nonzero configuration-valid-byte path is reconstructed.
"""
import math
from reference.central_impulse import f32
from .snow_post_pending import four
from .snow_prepass_gain import prepass_direction_gain
from .snow_prepass_direction import slope_projection_direction
from .snow_prepass_projection import project_prepass_direction
from .snow_prepass_angle import control_prepass_angle
from .snow_prepass_finish import finish_prepass_basis
from .snow_axis_rotation import rotate_basis_axis


def basis_prepass(state, curves, slope_angle, sine, cosine, reciprocal_sqrt_seed):
    """Return basis, auxiliary direction, gate state and stage diagnostics.

    Caller provides a coherent entry snapshot and named curve services. This
    does not resolve pointers, execute protected invalid configuration, or
    establish live callback phase/ownership. No input state is mutated.
    """
    for key in ('config_valid_byte','immersion_selector_byte','mode_byte'):
        if not isinstance(state[key],int) or not 0 <= state[key] <= 255:
            raise ValueError('Raw uint8 required: '+key)
    if state['config_valid_byte']==0:
        raise ValueError('Protected invalid-configuration path is unresolved')
    frame=[four(v) for v in state['frame_basis']]
    if len(frame)!=3:raise ValueError('Three published frame vectors required')
    mode=state['mode_byte']
    selected=frame[1] if mode else four(state['incoming_axis0'])
    primary=f32(state['primary_immersion'])
    immersion=primary if state['immersion_selector_byte']==1 else f32(state['alternate_immersion'])
    if not math.isfinite(primary) or not math.isfinite(immersion):
        raise ValueError("Finite immersion inputs required")
    replace=primary<=0
    normal=four(state['normal'])
    gain=None
    if normal[2]<f32(.999):
        gain=prepass_direction_gain(state['direction_control'],state['special_byte'],
                                   state['speed_argument'],lambda x: curves['direction_control'](x),
                                   lambda x: curves['direction_speed'](x))
    direction=slope_projection_direction(normal,state.get('rotation_axis'),selected,
                                         gain,state.get('depth'),slope_angle,sine,cosine,
                                         reciprocal_sqrt_seed)
    projection=project_prepass_direction(selected,direction['direction'],frame[2],
                                         reciprocal_sqrt_seed)
    angle=control_prepass_angle(**state['control_angle'], mode_byte=mode,
                                speed_argument=state['speed_argument'],
                                immersion_argument=immersion,
                                speed_curve=lambda x: curves['control_speed'](x),
                                immersion_curve=lambda x: curves['control_immersion'](x))
    axis=projection['axis0']
    if angle['angle'] is not None:
        axis=rotate_basis_axis(axis,direction['direction'],angle['angle'],f32(1e-5),sine,cosine)
    finish=finish_prepass_basis(axis,direction['direction'],state['direct_angle'],
                               state['curve_angle'],state['speed_argument'],immersion,
                               replace,[selected,frame[2],frame[0]],lambda x: curves['finish_speed'](x),
                               lambda x: curves['finish_immersion'](x),sine,cosine,reciprocal_sqrt_seed)
    return {'basis':finish['basis'],'auxiliary_direction':direction['direction'],
            'gate_byte':angle['gate_byte'],'gate_written':angle['gate_written'],
            'replaced':replace,'direction_branch':direction['branch'],
            'projection_fallback':projection['used_fallback'],
            'control_angle':angle['angle'],'finish_curve_angle':finish['curve_angle']}
