"""Connected finite-domain basis callback with explicit curve/math services.

Evidence: CENTRAL_IMPULSE.md, Connected basis callback.
No live memory access, scheduler integration or native object lifetime handling.
"""
from .snow_post_pending import four
from .snow_basis_prepass import basis_prepass
from .snow_basis_dispatch import dispatch_basis


def basis_callback(enabled_byte, incoming_basis, prepass_state, override_state,
                   curves, slope_angle, sine, cosine, reciprocal_sqrt_seed):
    """Return local callback effects without mutating supplied containers.

    Disabled execution does not require stage inputs or services. Shared preferred
    state comes from override_state; initial axis comes from incoming_basis.
    """
    if not isinstance(enabled_byte,int) or not 0 <= enabled_byte <= 255:
        raise ValueError('Raw uint8 enabled flag required')
    if len(incoming_basis)!=3:raise ValueError('Three incoming vectors required')
    incoming=[four(v) for v in incoming_basis]
    if enabled_byte==0:
        return {'success':False,'basis':incoming,'cache_written':False,
                'auxiliary_written':False,'gate_written':False,'branch':'disabled'}
    pre=dict(prepass_state)
    pre['incoming_axis0']=incoming[0]
    pre['control_angle']=dict(pre['control_angle'])
    pre['control_angle']['preferred_byte']=override_state['preferred_byte']
    prepared=basis_prepass(pre,curves,slope_angle,sine,cosine,reciprocal_sqrt_seed)
    overrides=dict(override_state)
    overrides['basis']=prepared['basis']
    result=dispatch_basis(overrides,sine,cosine,reciprocal_sqrt_seed)
    result.update(success=True,auxiliary_written=True,
                  auxiliary_direction=prepared['auxiliary_direction'],
                  gate_written=prepared['gate_written'],gate_byte=prepared['gate_byte'],
                  prepass=prepared)
    return result
