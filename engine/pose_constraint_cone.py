"""Kind5 composition; LINK_SOLVER.md, Kind5 constraint composition."""
import math
import struct
from reference.central_impulse import f32
from .pose_constraint_point import build_pose_point_constraint,_xyz
from .pose_paired_angular_solver import _transform,_inverse_matrix
from .pose_primary_solver import _read
from .pose_constraint_hinge import _cross
from .pose_constraint_limit_geometry import pose_angular_limit_geometry
from .pose_constraint_limit import build_pose_angular_limit_row
from .pose_constraint_target import prepare_pose_target_frame
from .pose_constraint_vector_drive import build_pose_vector_drive_row
from .pose_scalar_trig import scalar_sin_cos
from .pose_link_rotation import quaternion_basis
from .snow_pose_angle import pose_row_angle


def _inverse_target(matrix):
    a,b,c=matrix[0][:3];d,e,f=matrix[1][:3];g,h,i=matrix[2][:3]
    sub=lambda x,y,z,w:f32(f32(x*y)-f32(z*w))
    aa=sub(e,i,f,h);bb=sub(c,h,b,i);cc=sub(b,f,c,e)
    determinant=f32(f32(f32(a*aa)-f32(sub(b,i,c,h)*d))+f32(g*cc))
    cof=[[aa,bb,cc],[sub(g,f,d,i),sub(a,i,g,c),sub(d,c,a,f)],
         [sub(d,h,g,e),sub(g,b,a,h),sub(a,e,d,b)]]
    if abs(f32(determinant-1.))>f32(1e-6):
        if determinant==0:raise ValueError('Nonsingular target required')
        reciprocal=f32(1./determinant)
        cof=[[f32(reciprocal*v) for v in col] for col in cof]
    return [col+[0.] for col in cof]


def build_pose_cone_constraint(context,constraint,*,bodies,metadata,atan2,notify=None):
    """Append point, angular limits and optional vector drive; cone is our name."""
    first,second=struct.unpack_from('<2Q',constraint,8)
    b1,b2=bodies[first],bodies[second]
    frames=[[_xyz(b,o) for o in (0x40,0x50,0x60)] for b in (b1,b2)]
    single=not bool(struct.unpack_from('<H',metadata[struct.unpack_from('<Q',b2,0x30)[0]],0x50)[0]&0x8000)
    indices=[struct.unpack_from('<H',b,0x1c)[0] for b in (b1,b2)]
    swapped=bool(constraint[0x59]);config=bytes(constraint[0x70:0x144])
    if len(config)!=0xd4:raise ValueError('Complete retained kind5 configuration required')
    scalar=lambda off:struct.unpack_from('<f',config,off)[0]
    u=_transform(frames[0],_read(config,0x20));v=_transform(frames[1],_read(config,0x30))
    p=_transform(frames[0],_read(config,0x40));q=_transform(frames[1],_read(config,0x50))
    build_pose_point_constraint(context,constraint,bodies=bodies,metadata=metadata)
    def length(a):
        s=[f32(x*x) for x in a[:3]]
        return f32(math.sqrt(f32(f32(s[0]+s[1])+f32(s[2]+0.))))
    axis=_cross(u,v)
    if length(axis)<f32(1e-4):
        axis=_cross(v,[1.,0.,0.,0.])
        if length(axis)<f32(1e-4):axis=_cross(v,[0.,1.,0.,0.])
    norm=length(axis)
    if norm==0:raise ValueError('Nonzero kind5 correction axis required')
    reciprocal=f32(1./norm);axis=[f32(x*reciprocal) for x in axis]
    angle=pose_row_angle(axis,u,v,atan2)['angle']
    azimuth=pose_row_angle(u if swapped else v,p if swapped else q,axis,atan2)['angle']
    correction,error=pose_angular_limit_geometry([-angle]*4,[azimuth]*4,
        [scalar(0x60)]*4,[scalar(0x64)]*4,axis,v if swapped else u)
    def complete(row):struct.pack_into('<2H',context,row,*indices)
    def limit(axis,coordinate,sign,offset,term,mix):
        complete(build_pose_angular_limit_row(context,single=single,axis=axis,
            coordinate=coordinate,sign=[sign]*4,offset=[offset]*4,
            response_term=[term]*4,response_mix=[mix]*4))
    limit(correction,error,1.,0.,scalar(0xc4),scalar(0xc8))
    if config[0x68]:
        sine,cosine=scalar_sin_cos(f32(angle*.5))
        rotation=[col+[0.] for col in quaternion_basis([f32(x*sine) for x in axis[:3]]+[cosine])]
        twist=pose_row_angle(u,p,_transform(rotation,q),atan2)['angle']
        for direction in (u,v):
            for sign in (1.,-1.):limit(direction,[twist]*4,sign,scalar(0x6c),scalar(0xcc),scalar(0xd0))
    if config[0x70]:
        target=bytearray(48)
        # Native getter reads live inline config, unlike the earlier snapshot.
        prepare_pose_target_frame(constraint[0x70:],target,swapped=bool(constraint[0x59]),atan2=atan2)
        desired=[_xyz(target,o) for o in (0,16,32)]
        if swapped:desired=_inverse_target(desired)
        inverse=_inverse_matrix(frames[1])
        relative=[_transform(inverse,col) for col in frames[0]]
        complete(build_pose_vector_drive_row(context,single=single,cap=[scalar(0x74)]*4,
            strength=[scalar(0x78)]*4,gain=[scalar(0xc0)]*4,frame_a=desired,
            frame_b=relative,output_frame=frames[0],additive=_read(config,0xb0)))
        if not config[0x71]:
            token=struct.unpack_from('<Q',constraint,8)[0];body=bodies[token]
            if struct.unpack_from('<Q',body,0x10)[0] and struct.unpack_from('<Q',metadata[struct.unpack_from('<Q',body,0x30)[0]],0x20)[0]:
                if notify is None:raise ValueError('Reached kind5 body notification requires service')
                notify(token,2)
    return 1
