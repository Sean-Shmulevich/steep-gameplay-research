"""Pose quaternion kernels; LINK_SOLVER.md, Quaternion inputs to angular drive."""
import math
from reference.central_impulse import f32
from .pose_constraint_limit import _vector


def multiply_pose_quaternions(first, second):
    """Hamilton product in XYZW order, with retained scalar float32 ordering.

    Does not normalize either operand or canonicalize the result's sign.
    """
    x,y,z,w = _vector(first)
    a,b,c,d = _vector(second)
    return [
        f32(f32(f32(f32(c*y)-f32(b*z))+f32(a*w))+f32(x*d)),
        f32(f32(f32(f32(a*z)-f32(c*x))+f32(b*w))+f32(y*d)),
        f32(f32(f32(f32(b*x)-f32(a*y))+f32(c*w))+f32(z*d)),
        f32(f32(w*d)-f32(f32(f32(b*y)+f32(a*x))+f32(c*z))),
    ]


def pose_matrix_to_quaternion(columns):
    """Convert three XYZ columns to XYZW, without repair or normalization.

    Fourth lanes, when present, are unused. Strict comparisons preserve W/X/Y/Z
    priority on equal candidate values. Finite, nonoverflowing inputs required.
    """
    if len(columns) != 3 or any(len(c) not in (3,4) for c in columns):
        raise ValueError('Three XYZ or XYZW columns required')
    c = [[f32(v) for v in col[:3]] for col in columns]
    if not all(math.isfinite(v) for col in c for v in col):
        raise ValueError('Finite matrix XYZ values required')
    xx,xy,xz = c[0]
    yx,yy,yz = c[1]
    zx,zy,zz = c[2]
    candidates = [f32(f32(yy+xx)+zz), f32(f32(xx-yy)-zz),
                  f32(f32(yy-xx)-zz), f32(f32(zz-xx)-yy)]
    chosen = 0
    for i in (1,2,3):
        if candidates[i] > candidates[chosen]:
            chosen = i
    root = f32(math.sqrt(f32(candidates[chosen]+1.)))
    major = f32(root*.5)
    scale = f32(.25/major)
    add = lambda a,b: f32(f32(a+b)*scale)
    sub = lambda a,b: f32(f32(a-b)*scale)
    if chosen == 0:
        return [sub(yz,zy), sub(zx,xz), sub(xy,yx), major]
    if chosen == 1:
        return [major, add(yx,xy), add(zx,xz), sub(yz,zy)]
    if chosen == 2:
        return [add(yx,xy), major, add(zy,yz), sub(zx,xz)]
    return [add(zx,xz), add(zy,yz), major, sub(xy,yx)]
