"""Post-prepass basis selection; not the callback's enabled gate or prepass.

Evidence: CENTRAL_IMPULSE.md, Connected post-prepass basis dispatch.
State is caller-supplied after the prepass. Names describe local roles only.
"""
import math
from reference.central_impulse import f32
from .snow_post_pending import four
from .snow_basis_angles import apply_basis_angles, apply_preferred_basis
from .snow_basis_override import normalize_override_triplet, align_override_basis


def dispatch_basis(state, sine, cosine, reciprocal_sqrt_seed):
    """Return detached output/cache, pending state and an authored branch label.

    Only selected branch operands are required. The raw flags are uint8 values.
    No pointer resolution, phase consistency or native atomicity is supplied.
    """
    def byte(name):
        value = state[name]
        if not isinstance(value, int) or not 0 <= value <= 255:
            raise ValueError('Raw uint8 required: '+name)
        return value
    preferred = False
    if byte('preferred_byte'):
        vector = four(state['preferred_gate_vector'])
        if not all(math.isfinite(x) for x in vector):
            raise ValueError('Finite preferred gate vector required')
        if any(abs(x) > f32(1e-5) for x in vector):
            preferred = byte('inhibit_byte') == 0
    if preferred:
        rebuild = byte('rebuild_byte')
        result = apply_preferred_basis(
            state['saved_basis'], state.get('preferred_axis'),
            state.get('preferred_angle'), state['secondary_angle'], rebuild,
            byte('clear_secondary_byte'), sine, cosine, reciprocal_sqrt_seed)
    elif byte('explicit_triplet_byte'):
        basis = normalize_override_triplet(state['explicit_triplet'], reciprocal_sqrt_seed)
        result = {'branch': 'explicit_triplet', 'basis': basis,
                  'saved_basis': [v[:] for v in basis],
                  'secondary_angle': f32(state['secondary_angle']),
                  'clear_secondary_byte': byte('clear_secondary_byte')}
    elif byte('alignment_byte'):
        basis = align_override_basis(state['basis'], state['direction'], reciprocal_sqrt_seed)
        result = {'branch': 'alignment', 'basis': basis,
                  'saved_basis': [v[:] for v in basis],
                  'secondary_angle': f32(state['secondary_angle']),
                  'clear_secondary_byte': byte('clear_secondary_byte')}
    else:
        result = apply_basis_angles(state['basis'], state['primary_angle'],
                                   state['secondary_angle'], byte('rebuild_byte'),
                                   byte('clear_secondary_byte'), sine, cosine,
                                   reciprocal_sqrt_seed)
    result['cache_written'] = result['branch'] != 'preferred_reuse'
    return result
