"""Finite point-impulse wrapper with supplied world inertia.

CENTRAL_IMPULSE.md, Point-impulse body arithmetic. Matrix-cache construction and
backend dispatch remain external. Basis and inertia are row-major 3x3 inputs.
"""
from reference.central_impulse import central_impulse, f32, vector


def apply_point_impulse(linear, angular, impulse, point, inverse_mass,
                        local_center, translation, basis, inverse_world_inertia,
                        *, kind=0, flags=0, force=False):
    result = central_impulse(linear, angular, impulse, inverse_mass,
                             kind=kind, flags=flags, force=force)
    if not result['velocity_write_enabled']:
        return dict(result, center=None, angular_impulse=None)
    local, position, p, j = map(vector, (local_center, translation, point, impulse))
    if len(basis) != 3 or len(inverse_world_inertia) != 3:
        raise ValueError('3x3 basis and world inverse inertia required')
    basis = [vector(row) for row in basis]
    inertia = [vector(row) for row in inverse_world_inertia]
    center = [f32(f32(f32(f32(local[1]*r[1])+f32(local[0]*r[0])) +
                           f32(local[2]*r[2]))+t) for r,t in zip(basis,position)]
    arm = [f32(x-y) for x,y in zip(p,center)]
    torque = [f32(f32(arm[b]*j[c])-f32(arm[c]*j[b]))
              for b,c in [(1,2),(2,0),(0,1)]]
    delta = [f32(f32(f32(r[1]*torque[1])+f32(r[0]*torque[0]))+
                 f32(r[2]*torque[2])) for r in inertia]
    result['angular'] = tuple(f32(d+w) for d,w in zip(delta,vector(angular)))
    return dict(result, center=center, angular_impulse=torque)


def world_inverse_inertia(basis, local_inverse_inertia):
    """Native two-stage matrix product: local * transpose(basis), then basis * it.

    No orthonormality or symmetry substitution; finite row-major 3x3 inputs.
    This evaluates stored inputs, not their producer or cache freshness.
    """
    if len(basis) != 3 or len(local_inverse_inertia) != 3:
        raise ValueError('3x3 matrices required')
    rotation = [vector(row) for row in basis]
    local = [vector(row) for row in local_inverse_inertia]
    def product(a, b):
        return [[f32(f32(f32(a[i][0]*b[0][j])+f32(a[i][1]*b[1][j]))+
                     f32(a[i][2]*b[2][j])) for j in range(3)] for i in range(3)]
    transposed = list(zip(*rotation))
    return product(rotation, product(local, transposed))
