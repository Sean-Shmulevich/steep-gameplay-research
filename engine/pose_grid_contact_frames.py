"""Terrain caller frames; LINK_SOLVER.md, Terrain inverse and relative frames."""
import math
from reference.central_impulse import f32


def grid_contact_frames(terrain_frame, other_frame):
    """Return inverse terrain frame and other frame expressed in terrain space.

    Four XYZ rows per frame. Finite nonsingular arithmetic required; singular
    rejection is authored and does not emulate native exceptional division.
    """
    f,g=[[list(map(f32,row)) for row in frame] for frame in (terrain_frame,other_frame)]
    def cross(a,b):
        return [f32(f32(a[(j+1)%3]*b[(j+2)%3])-f32(a[(j+2)%3]*b[(j+1)%3])) for j in range(3)]
    def dot(a,b):
        p=[f32(x*y) for x,y in zip(a,b)]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.))
    cofactors=[cross(f[1],f[2]),cross(f[2],f[0]),cross(f[0],f[1])]
    determinant=dot(f[0],cofactors[0])
    if determinant==0 or not math.isfinite(determinant):
        raise ValueError('Finite nonsingular terrain frame required')
    reciprocal=f32(1./determinant)
    c=[[f32(v*reciprocal) for v in row] for row in cofactors]
    basis=[[c[j][i] for j in range(3)] for i in range(3)]
    def direction(v):
        return [f32(f32(f32(basis[1][j]*v[1])+f32(basis[0][j]*v[0]))
                    +f32(basis[2][j]*v[2])) for j in range(3)]
    translation=direction([-v for v in f[3]])
    relative=[direction(row) for row in g[:3]]
    relative.append([f32(f32(f32(f32(basis[0][j]*g[3][0])+translation[j])
                                  +f32(basis[1][j]*g[3][1]))
                             +f32(basis[2][j]*g[3][2])) for j in range(3)])
    return basis+[translation],relative
