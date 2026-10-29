"""Kind5 target preparation; LINK_SOLVER.md, Bounded drive target frame."""
import math
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read
from .pose_paired_angular_solver import _transform
from .pose_link_rotation import quaternion_basis
from .pose_scalar_trig import scalar_sin_cos
from .snow_pose_angle import pose_row_angle


def prepare_pose_target_frame(config, destination, *, swapped, atan2):
    """Copy and limit target XYZ columns, preserving destination padding lanes.

    Config is the inline kind5 record, not the whole constraint. Atan2 remains
    an explicit service. Output is modified in place; no row allocation occurs.
    """
    if len(config)<0xac or len(destination)<0x30:
        raise ValueError('Complete retained target configuration and destination required')
    cols=[list(struct.unpack_from('<3f',config,off))+[0.] for off in (0x80,0x90,0xa0)]
    if not all(math.isfinite(v) for col in cols for v in col):
        raise ValueError('Finite target columns required')
    for i,col in enumerate(cols):struct.pack_into('<3f',destination,16*i,*col[:3])
    frame=[[cols[j][i] for j in range(3)]+[0.] for i in range(3)] if swapped else cols
    u=_transform(frame,_read(config,0x20));t=_transform(frame,_read(config,0x40))
    v,reference=_read(config,0x30),_read(config,0x50)
    cross=[f32(f32(u[j]*v[k])-f32(v[j]*u[k])) for j,k in ((1,2),(2,0),(0,1))]+[0.]
    squares=[f32(x*x) for x in cross[:3]]
    length=f32(math.sqrt(f32(f32(squares[0]+squares[1])+f32(squares[2]+0.))))
    axis=reference[:] if length<f32(1e-4) else [f32(x/length) for x in cross]
    angle=pose_row_angle(axis,v,u,atan2)['angle']
    a,b=struct.unpack_from('<2f',config,0x60)
    def rotation(axis,angle):
        s,c=scalar_sin_cos(f32(angle*.5))
        return [col+[0.] for col in quaternion_basis([f32(x*s) for x in axis[:3]]+[c])]
    def compose(rot):
        old=[list(struct.unpack_from('<3f',destination,i*16)) for i in range(3)]
        for i,col in enumerate(old):
            out=[f32(f32(f32(rot[0][j]*col[0])+f32(rot[1][j]*col[1]))+f32(rot[2][j]*col[2])) for j in range(3)]
            struct.pack_into('<3f',destination,i*16,*out)
    smaller=a if f32(b-a)>=0 else b
    if angle>smaller:
        quarter=_transform(rotation(axis,f32(math.pi/2)),v)
        azimuth=pose_row_angle(v,reference,quarter,atan2)['angle']
        sine,cosine=scalar_sin_cos(azimuth)
        ca,sb=f32(cosine*a),f32(sine*b)
        denom=f32(math.sqrt(f32(f32(sb*sb)+f32(ca*ca))))
        if denom==0:raise ValueError('Nonzero angular bound denominator required')
        limit=f32(f32(b*a)/denom)
        if angle>limit:compose(rotation(axis,f32(limit-angle)))
    if config[0x68]:
        transformed=_transform(rotation(axis,angle),t)
        twist=pose_row_angle(v,reference,transformed,atan2)['angle']
        bound=struct.unpack_from('<f',config,0x6c)[0]
        if twist>bound:correction=f32(bound-twist)
        elif twist < -bound:correction=f32(-twist-bound)
        else:return
        compose(rotation(u,correction))
