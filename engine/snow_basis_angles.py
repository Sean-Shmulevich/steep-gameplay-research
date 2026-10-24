"""Recovered post-prepass fallback angle branches of the snow basis callback.

Evidence: CENTRAL_IMPULSE.md, Fallback basis angles and consumption.
Caller establishes reachability after preferred/triplet/alignment branches.
"""
import math
from reference.central_impulse import f32
from .snow_post_pending import four
from .snow_basis_override import _cross, _normalize
from .snow_axis_rotation import rotate_basis_axis


def apply_basis_angles(initial_basis, primary_angle, secondary_angle,
                       rebuild_byte, clear_secondary_byte, sine, cosine,
                       reciprocal_sqrt_seed):
    """Return detached output/cache and next pending-angle state.

    The two flags are raw uint8 values. Trig and rsqrt services remain explicit.
    Finite, nonsingular branch inputs only; errors are authored API behavior.
    """
    if len(initial_basis) != 3:
        raise ValueError('Three basis vectors required')
    for flag in (rebuild_byte, clear_secondary_byte):
        if not isinstance(flag, int) or not 0 <= flag <= 255:
            raise ValueError('Raw uint8 flags required')
    basis = [four(v) for v in initial_basis]
    primary, secondary = f32(primary_angle), f32(secondary_angle)
    if not math.isfinite(primary) or not math.isfinite(secondary):
        raise ValueError('Finite angles required')
    clear = clear_secondary_byte
    branch = 'retain'
    if primary != 0 or (secondary != 0 and rebuild_byte != 0):
        branch = 'primary' if primary != 0 else 'secondary'
        angle = primary if branch == 'primary' else secondary
        basis[0] = rotate_basis_axis(basis[0], basis[1], angle, f32(1e-5), sine, cosine)
        basis[2] = _normalize(_cross(basis[0], basis[1]), reciprocal_sqrt_seed)
        if branch == 'secondary':
            basis[0] = _normalize(_cross(basis[1], basis[2]), reciprocal_sqrt_seed)
            if clear != 0:
                secondary = 0.0
            clear = 0
    return {'branch': branch, 'basis': basis,
            'saved_basis': [v[:] for v in basis],
            'secondary_angle': secondary, 'clear_secondary_byte': clear}


def apply_preferred_basis(saved_basis, preferred_axis, preferred_angle,
                          secondary_angle, rebuild_byte, clear_secondary_byte,
                          sine, cosine, reciprocal_sqrt_seed):
    """Rebuild from saved axis 0 and a supplied axis, or reuse the saved basis.

    Evidence: CENTRAL_IMPULSE.md, Preferred basis rebuild. Caller establishes
    preferred-path eligibility. The no-rebuild path does not call math services.
    """
    if len(saved_basis) != 3:
        raise ValueError('Three saved basis vectors required')
    for flag in (rebuild_byte, clear_secondary_byte):
        if not isinstance(flag, int) or not 0 <= flag <= 255:
            raise ValueError('Raw uint8 flags required')
    basis = [four(v) for v in saved_basis]
    if rebuild_byte == 0:
        return {'branch': 'preferred_reuse', 'basis': basis,
                'saved_basis': [v[:] for v in basis],
                'secondary_angle': f32(secondary_angle),
                'clear_secondary_byte': clear_secondary_byte}
    basis[1] = four(preferred_axis)
    basis[2] = _normalize(_cross(basis[0], basis[1]), reciprocal_sqrt_seed)
    basis[1] = rotate_basis_axis(basis[1], basis[2], -f32(preferred_angle),
                                f32(1e-5), sine, cosine)
    basis[0] = _normalize(_cross(basis[1], basis[2]), reciprocal_sqrt_seed)
    result = apply_basis_angles(basis, 0., secondary_angle, rebuild_byte,
                                clear_secondary_byte, sine, cosine,
                                reciprocal_sqrt_seed)
    result['branch'] = 'preferred_rebuild'
    return result
