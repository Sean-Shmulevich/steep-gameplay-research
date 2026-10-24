"""Recovered geometric four-index selector with fixed-angle rotation and optional supplied service.

Evidence: CENTRAL_IMPULSE.md, Geometric four-record selection.
"""
import math
from reference.central_impulse import f32
from .pose_link_rotation import selector_rotation_basis

SELECTOR_ANGLE=f32(0.6456422805786133)
LIMIT=f32(3.4028234663852886e38)


def select_pose_link_rows(points, normal, *, rotation_basis=selector_rotation_basis):
    """Return four indices, allowing duplicates and selecting later ties.

    The default matrix uses the recovered fixed-angle half-sine/cosine values.
    Callers can supply a different observed matrix service explicitly.
    Finite nonempty points and a nondegenerate normal/tangent are API preconditions.
    """
    points=[[f32(x) for x in p] for p in points];normal=[f32(x) for x in normal]
    if not points or len(normal)!=3 or any(len(p)!=3 for p in points):
        raise ValueError('Nonempty XYZ points and XYZ normal required')
    if not all(math.isfinite(x) for p in points+[normal] for x in p):
        raise ValueError('Finite geometry required')
    center=[0.,0.,0.];count=0.
    for p in points:
        center=[f32(a+b) for a,b in zip(center,p)];count=f32(count+1.)
    center=[f32(x/count) for x in center]
    x,y,z=normal;ax,ay,az=map(abs,normal)
    if f32(min(ax,ay)-az)<0:
        tangent=[z,0.,-x] if f32(ay-ax)<0 else [0.,z,-y]
    else:tangent=[y,-x,0.]
    def dot(a,b):
        p=[f32(x*y) for x,y in zip(a,b)]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.))
    length=f32(math.sqrt(dot(tangent,tangent)))
    if length==0 or not math.isfinite(length):raise ValueError('Nondegenerate tangent required')
    inverse=f32(1./length);tangent=[f32(x*inverse) for x in tangent]
    basis=[[f32(x) for x in row] for row in rotation_basis(normal,SELECTOR_ANGLE)]
    if len(basis)!=3 or any(len(row)!=3 for row in basis):raise ValueError('Three XYZ rotation rows required')
    axis=[f32(f32(f32(basis[1][j]*tangent[1])+f32(basis[0][j]*tangent[0]))+
              f32(basis[2][j]*tangent[2])) for j in range(3)]
    minimum=LIMIT;maximum=-LIMIT;low=[0.,0.,0.];high=[0.,0.,0.]
    for p in points:
        value=dot([f32(a-b) for a,b in zip(p,center)],axis)
        if f32(minimum-value)>=0:minimum=value;low=p
        if f32(value-maximum)>=0:maximum=value;high=p
    span=[f32(a-b) for a,b in zip(low,high)]
    cross=[f32(f32(span[(j+2)%3]*normal[(j+1)%3])-
               f32(span[(j+1)%3]*normal[(j+2)%3])) for j in range(3)]
    extrema=[LIMIT,-LIMIT,LIMIT,-LIMIT];indices=[0,0,0,0]
    for i,p in enumerate(points):
        delta=[f32(a-b) for a,b in zip(p,center)]
        a,b=dot(delta,span),dot(delta,cross)
        for k,value in enumerate((a,a,b,b)):
            difference=f32(extrema[k]-value) if k%2==0 else f32(value-extrema[k])
            if difference>=0:extrema[k]=value;indices[k]=i
    return dict(indices=indices,center=center,tangent=tangent,axis=axis,span=span,cross=cross)


def reduce_pose_link_records(collection, *, rotation_basis=selector_rotation_basis):
    """Apply the inspected caller's >4 gate and snapshot-copy four selected rows.

    Active slots are 48-byte records. Normal is first record XYZ; selection points
    are each record's XYZ at+16. Inactive tail entries are preserved.
    """
    import struct
    count=collection['count']
    if count<=4:return None
    records=collection['slots'][:count]
    if len(records)!=count or any(len(r)!=48 for r in records):
        raise ValueError('Retained 48-byte active records required')
    selection=select_pose_link_rows([struct.unpack_from('<3f',r,16) for r in records],
        struct.unpack_from('<3f',records[0]),rotation_basis=rotation_basis)
    chosen=[bytes(records[i]) for i in selection['indices']]
    collection['count']=4
    collection['slots'][:4]=chosen
    return selection
