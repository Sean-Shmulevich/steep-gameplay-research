"""Recovered provider pose conversion; XYZW quaternions, supplied pose inputs.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Skeleton provider pose conversion.
No quaternion normalization or selector-to-bone interpretation is supplied.
"""
import math
from reference.transform_composition import _f32 as f


def convert_skeleton_provider_pose(position, rotation, base_position, base_rotation,
                                   already_transformed):
    vectors = [position, rotation, base_position, base_rotation]
    if any(len(v) != 4 or not all(math.isfinite(x) for x in v) for v in vectors):
        raise ValueError('four finite four-lane vectors required')
    if type(already_transformed) is not bool:
        raise ValueError('boolean conversion gate required')
    p, c, b, q = [[f(x) for x in v] for v in vectors]
    if already_transformed:
        return dict(position=p[:3], rotation=c)
    dot = f(f(p[0]*q[0]) + f(f(p[1]*q[1]) + f(p[2]*q[2])))
    cross = [f(f(q[1]*p[2])-f(q[2]*p[1])),
             f(f(q[2]*p[0])-f(q[0]*p[2])),
             f(f(q[0]*p[1])-f(q[1]*p[0]))]
    weight = f(f(q[3]*q[3]) - .5)
    pos = [f(f(f(f(f(dot*q[i])+f(cross[i]*q[3])) + f(weight*p[i]))*2) + b[i])
           for i in range(3)]
    tx = [f(q[0]*c[3]), f(-q[0]*c[2]), f(q[0]*c[1]), f(-q[0]*c[0])]
    ty = [f(q[1]*c[2]), f(q[1]*c[3]), f(-q[1]*c[0]), f(-q[1]*c[1])]
    tz = [f(-q[2]*c[1]), f(q[2]*c[0]), f(q[2]*c[3]), f(-q[2]*c[2])]
    rot = [f(tz[i] + f(f(f(q[3]*c[i])+tx[i])+ty[i])) for i in range(4)]
    return dict(position=pos, rotation=rot)
