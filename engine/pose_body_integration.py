"""Recovered transform update for the constructor-selected body class.

Evidence: LINK_SOLVER.md, Constructor-selected body transform integration.
General half-angle trigonometric responses remain a supplied service.
"""
import math
import struct
from reference.central_impulse import f32
from engine.pose_link_rotation import quaternion_basis

ANGULAR_THRESHOLD = 2.0**-23


def integrate_pose_body(body, scalar, *, half_angle_trig=None):
    """Update basis/translation in retained raw body storage.

    Finite, nondegenerate inputs only. half_angle_trig(half_angle) returns the
    supplied scalar-library sine and cosine responses. No assumed library or
    transcendental approximation is used. Motion and other body bytes persist.
    """
    if len(body) < 0x1b8:
        raise ValueError('Complete retained body fields required')
    def read(off):
        v = list(struct.unpack_from('<3f', body, off))
        if not all(math.isfinite(x) for x in v):
            raise ValueError('Finite body fields required')
        return v
    s = f32(scalar)
    if not math.isfinite(s):
        raise ValueError('Finite scalar required')
    basis = [read(off) for off in (0x40, 0x50, 0x60)]
    position, offset = read(0x70), read(0x128)
    linear, angular = read(0x1a0), read(0x1ac)
    def transform(b, v):
        return [f32(f32(f32(b[1][j]*v[1])+f32(b[0][j]*v[0]))+
                    f32(b[2][j]*v[2])) for j in range(3)]
    def norm(v):
        return f32(math.sqrt(f32(f32(f32(v[0]*v[0])+f32(v[1]*v[1]))+
                                 f32(v[2]*v[2]))))
    def normalize(v):
        length = norm(v)
        if not length > 0:
            raise ValueError('Nondegenerate basis required')
        inv = f32(1.0/length)
        return [f32(x*inv) for x in v]
    def cross(a,b):
        return [f32(f32(a[1]*b[2])-f32(a[2]*b[1])),
                f32(f32(a[2]*b[0])-f32(a[0]*b[2])),
                f32(f32(a[0]*b[1])-f32(a[1]*b[0]))]
    center = [f32(x+y) for x,y in zip(position, transform(basis,offset))]
    speed = norm(angular)
    if speed > ANGULAR_THRESHOLD:
        if half_angle_trig is None:
            raise ValueError('Scalar-library half-angle response required')
        # Axis denominator sums y squared before x squared in this helper.
        denominator = f32(math.sqrt(f32(f32(f32(angular[1]*angular[1])+
                                           f32(angular[0]*angular[0]))+
                                       f32(angular[2]*angular[2]))))
        inv = f32(1.0/denominator)
        axis = [f32(x*inv) for x in angular]
        half = f32(f32(speed*s)*0.5)
        sine, cosine = map(f32, half_angle_trig(half))
        rotation = quaternion_basis([f32(x*sine) for x in axis]+[cosine])
        rotated = [transform(rotation, row) for row in basis]
        first = normalize(rotated[0])
        projection = f32(f32(f32(first[1]*rotated[1][1])+
                             f32(first[0]*rotated[1][0]))+
                         f32(first[2]*rotated[1][2]))
        orthogonal = [f32(y-f32(x*projection)) for x,y in zip(first,rotated[1])]
        third = normalize(cross(first,orthogonal))
        basis = [first,cross(third,first),third]
    translated = [f32(x+f32(s*v)) for x,v in zip(center,linear)]
    position = [f32(x-y) for x,y in zip(translated,transform(basis,offset))]
    for off,v in zip((0x40,0x50,0x60,0x70),basis+[position]):
        struct.pack_into('<3f',body,off,*v)
