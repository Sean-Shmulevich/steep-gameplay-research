"""Recovered paired-point world geometry for the metadata-clear/single builder.

Evidence: LINK_SOLVER.md, Link paired-point world geometry.
"""
import math
from reference.central_impulse import f32


def link_point_geometry(first_frame, second_frame, first_point, second_point, first_offset128):
    """Use explicit local payload points, body frames and first-body local offset.

    No orthonormality or inverse-transform identity is assumed. Retain the first
    offset subtraction/readdition rather than simplifying to a direct transform.
    """
    def vector(v):
        if len(v)!=3:raise ValueError('Three components required')
        out=[f32(x) for x in v]
        if not all(math.isfinite(x) for x in out):raise ValueError('Finite components required')
        return out
    frames=[]
    for frame in (first_frame,second_frame):
        if len(frame['basis'])!=3:raise ValueError('Three basis rows required')
        frames.append(([vector(v) for v in frame['basis']],vector(frame['translation'])))
    (a,ta),(b,tb)=frames
    p1,p2,c=map(vector,(first_point,second_point,first_offset128))
    def transform(rows,v):
        return [f32(f32(rows[2][j]*v[2])+f32(f32(rows[0][j]*v[0])+f32(rows[1][j]*v[1]))) for j in range(3)]
    def add(a,b):return [f32(x+y) for x,y in zip(a,b)]
    center_world=add(ta,transform(a,c))
    local=[f32(p1[i]-c[i]) for i in range(3)]
    first_arm=transform(a,local)
    second_arm=transform(b,p2)
    first_world=add(first_arm,center_world)
    second_world=add(tb,second_arm)
    return dict(first_center_world=center_world,first_arm=first_arm,second_arm=second_arm,
                first_world=first_world,second_world=second_world,
                separation=[f32(second_world[i]-first_world[i]) for i in range(3)])
