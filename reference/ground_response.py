"""Composed recovered helper stages with caller-supplied runtime observations.

No live hooks, asset selection, locks, body writes or whole-engine equivalence.
See the central impulse guide's composed helper contract.
"""
from dataclasses import dataclass
from reference.central_impulse import (
    f32, helper_entry_eligible, helper_velocity_history, helper_force_geometry,
    helper_force_scale, helper_direct_impulses, helper_response_filter,
)


@dataclass(frozen=True)
class HelperState:
    previous_velocity: tuple
    current_velocity: tuple
    rate: float
    displacement: float


def update(state, observation, curves, reciprocal_sqrt, *, force, submission):
    """Evaluate entry -> history -> geometry -> scale -> submission -> filter.

    curves supplies entry/a/b callables for already-selected runtime curves.
    force supplies helper_force_scale scalar inputs except curve_a, curve_b and
    alignment. submission supplies helper_direct_impulses inputs except scale,
    dt, direction and override_byte. observation supplies current_velocity, dt,
    contact_fraction, auxiliary_scalar, direction_input, reference_axis,
    source_vector, curve_a_input and curve_b_input.

    Submissions are ordered plans, not body mutations. The filter uses velocity
    sampled before those submissions, as in the inspected helper.
    """
    entry_value = curves['entry'](force['speed_scalar'])
    entered = helper_entry_eligible(entry_value, observation['contact_fraction'],
                                   observation['auxiliary_scalar'], force['override_a'], force['override_b'])
    if not entered:
        return {'state':state, 'entered':False, 'submissions':(), 'publication':None}
    history = helper_velocity_history(state.current_velocity, observation['current_velocity'], observation['dt'])
    geometry = helper_force_geometry(observation['direction_input'], observation['reference_axis'],
                                     observation['source_vector'], reciprocal_sqrt)
    scale = None
    submissions = ()
    # The speed gate precedes both force-curve calls; the positive-factor gate
    # follows them. Preserve this ordering even when it yields no impulses.
    ceiling = f32(f32(force.get('pivot',15))*2)
    speed_gate = f32(force['speed_scalar']) < ceiling or force['override_a'] or force['override_b']
    if geometry['eligible'] and speed_gate:
        a = curves['a'](observation['curve_a_input'])
        b = curves['b'](observation['curve_b_input'])
        scale = helper_force_scale(curve_a=a,curve_b=b,alignment=geometry['alignment'],**force)
        if scale['eligible']:
            plan = helper_direct_impulses(scale['scale'],observation['dt'],geometry['direction'],
                                         override_byte=force['override_a'],**submission)
            submissions = plan['submissions']
    filtered = helper_response_filter(state.rate,state.displacement,history['acceleration'],
                                      observation['reference_axis'],observation['dt'])
    next_state = HelperState(history['previous'],history['current'],filtered['rate'],filtered['displacement'])
    return {'state':next_state, 'entered':True, 'geometry':geometry,'scale':scale,
            'submissions':submissions,'publication':filtered['published'],'filter':filtered}


def compile_curves(ground_stick_settings):
    """Bind one explicitly selected authored groundStickSettings object.

    Uses mappings established in the snow research. This does not select sport,
    normal/fast profile, runtime ownership or dynamic tuning. Input payloads are
    caller-owned and are not bundled with this implementation.
    """
    from functools import partial
    from reference.runtime_curve import compile_samples, evaluate
    mapping = {'entry':'forceSpeedCurve','a':'legCoilCurve','b':'forceDepthCurve'}
    curves = {}
    for role, field in mapping.items():
        data = ground_stick_settings[field]
        table = compile_samples(data['domain'],data['$array'])
        curves[role] = partial(evaluate, **table)
    return curves
