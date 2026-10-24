"""Recovered signed angular helper for pose solver rows.

Evidence: CENTRAL_IMPULSE.md, Pose row angular helper.
The atan2 service is explicit; platform math is not native bit-equivalence.
"""
import math
from reference.central_impulse import f32


def pose_row_angle(axis, reference, target, atan2):
    """atan2(reference dot (axis cross target), reference dot target).

    No normalization or degeneracy repair. XYZ operations retain float32 order;
    supplied vectors have four lanes, and W products are masked before reduction.
    """
    if any(len(v)!=4 for v in (axis,reference,target)):raise ValueError('Four-lane vectors required')
    a,r,t=[list(map(f32,v)) for v in (axis,reference,target)]
    if not all(math.isfinite(x) for v in (a,r,t) for x in v):raise ValueError('Finite vectors required')
    cross=[f32(f32(a[j]*t[k])-f32(t[j]*a[k])) for j,k in ((1,2),(2,0),(0,1))]
    def dot(v):
        p=[f32(r[i]*v[i]) for i in range(3)]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.))
    numerator=dot(cross);denominator=dot(t)
    angle=f32(atan2(numerator,denominator))
    if not math.isfinite(angle):raise ValueError('Finite angular service result required')
    return dict(angle=angle,numerator=numerator,denominator=denominator)
