"""Kind2 translation stage; LINK_SOLVER.md, Kind2 translation assembly."""
import struct
from reference.central_impulse import f32
from .pose_constraint_point import _xyz,build_pose_point_constraint
from .pose_primary_solver import _read
from .pose_paired_angular_solver import _transform
from .pose_constraint_translation import build_pose_translation_row,build_pose_translation_limit_pair
from .snow_pose_solver_counts import HARD_THRESHOLD


def prepare_pose_axis_constraint(constraint, *, bodies, metadata):
    """Snapshot inline record and derive world anchors, axes and lever arms."""
    first,second=struct.unpack_from('<2Q',constraint,8)
    body=[bodies[first],bodies[second]]
    config=bytes(constraint[0x70:0x190])
    if len(config)!=0x120:raise ValueError('Complete kind2 inline record required')
    single=not bool(struct.unpack_from('<H',metadata[struct.unpack_from('<Q',body[1],0x30)[0]],0x50)[0]&0x8000)
    frames=[[_xyz(b,off) for off in (0x40,0x50,0x60)] for b in body]
    points=[];arms=[];axes=[]
    for endpoint,(b,frame) in enumerate(zip(body,frames)):
        offset=endpoint*0x40;anchor=_read(config,offset);position=_xyz(b,0x70)
        points.append([f32(f32(frame[2][j]*anchor[2])+f32(f32(f32(frame[0][j]*anchor[0])+position[j])+f32(frame[1][j]*anchor[1]))) for j in range(4)])
        center=[0.]*4 if endpoint==1 and single else _xyz(b,0x128)
        arms.append(_transform(frame,[f32(a-c) for a,c in zip(anchor,center)]))
        axes.append([_transform(frame,_read(config,offset+16*i)) for i in (1,2,3)])
    return dict(config=config,single=single,points=points,arms=arms,axes=axes,
                body_indices=[struct.unpack_from('<H',b,0x1c)[0] for b in body])


def build_pose_axis_translations(context,constraint,*,bodies,metadata,prepared=None):
    """Emit only kind2's translation stage, including constraint feedback indices.

    Returns prepared inputs for later angular composition. Angular rows and
    drives are deliberately not supplied by this stage API.
    """
    data=prepare_pose_axis_constraint(constraint,bodies=bodies,metadata=metadata) if prepared is None else prepared
    config=data['config'];single=data['single'];indices=data['body_indices']
    rows=[struct.unpack_from('<I4f',config,off) for off in (0x80,0x94,0xa8)]
    if all(state==0 and stiffness>=HARD_THRESHOLD for state,lo,hi,stiffness,damping in rows):
        # Same point arithmetic, but kind2 stores its second anchor at config40.
        point_constraint=bytearray(constraint)
        point_constraint[0x80:0x90]=config[0x40:0x50]
        result=struct.unpack_from('<I',context,0x180)[0]
        build_pose_point_constraint(context,point_constraint,bodies=bodies,metadata=metadata)
        struct.pack_into('<I',constraint,0x190,result)
        return data
    arms=[v[:] for v in data['arms']]
    if constraint[0x59]!=config[0x11c]:
        axes=data['axes'][1]
        arms[1]=[f32(a+f32(p-q)) for a,p,q in zip(arms[1],*data['points'])]
    else:
        axes=data['axes'][0]
        arms[0]=[f32(a+f32(q-p)) for a,p,q in zip(arms[0],*data['points'])]
    common=dict(single=single,point_a=data['points'][0],point_b=data['points'][1],arm_a=arms[0],arm_b=arms[1])
    for i,(state,lo,hi,stiffness,damping) in enumerate(rows):
        soft=stiffness<HARD_THRESHOLD
        if state==0 or (state==2 and soft):
            row=build_pose_translation_row(context,axis=axes[i],**common,
                **(dict(stiffness=[stiffness]*4,damping=[damping]*4) if soft else {}))
            struct.pack_into('<HH',context,row,*indices)
            struct.pack_into('<I',constraint,0x190+4*i,struct.unpack_from('<I',context,row+4)[0])
        if state==2:
            build_pose_translation_limit_pair(context,axis=axes[i],body_indices=indices,
                first_bound=[lo]*4,second_bound=[hi]*4,**common)
    return data


def prepare_pose_angular_axes(prepared, *, swapped):
    """Return three (axis,reference,target) triples for reached angular rows."""
    import math
    from .pose_constraint_hinge import _cross
    a,b=prepared['axes']
    base,other,alternate=(b[2],a[0],a[1]) if swapped else (a[2],b[0],b[1])
    def dot(x,y):
        p=[f32(u*v) for u,v in zip(x[:3],y[:3])]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.))
    def normalized(v):
        length=f32(math.sqrt(dot(v,v)))
        if length==0:raise ValueError('Nondegenerate kind2 angular frame required')
        reciprocal=f32(1./length)
        return [f32(x*reciprocal) for x in v]
    if abs(dot(base,other))<f32(.9999):
        middle=normalized(_cross(base,other))
        secondary=normalized(_cross(middle,base))
    else:
        secondary=normalized(_cross(alternate,base))
        middle=normalized(_cross(base,secondary))
    if swapped:return [(a[0],a[1],middle),(middle,a[0],secondary),(b[2],middle,b[1])]
    return [(b[0],middle,b[1]),(middle,secondary,b[0]),(a[2],a[1],middle)]


def build_pose_axis_angular_rows(context,constraint,*,prepared,atan2):
    """Append kind2 angular state rows; optional drives remain separate."""
    from .snow_pose_hard_row import build_hard_pose_row
    from .snow_pose_soft_row import build_soft_pose_row
    from .snow_pose_angle import pose_row_angle
    from .pose_constraint_limit import build_pose_angular_limit_row
    config=prepared['config'];single=prepared['single'];indices=prepared['body_indices']
    records=[struct.unpack_from('<I4f',config,o) for o in (0xbc,0xd0,0xe4)]
    if all(r[0]==1 for r in records):return
    triples=prepare_pose_angular_axes(prepared,swapped=bool(constraint[0x59]))
    u32=lambda o:struct.unpack_from('<I',context,o)[0]
    for (state,lo,hi,k,d),(axis,reference,target) in zip(records,triples):
        if state==1:continue
        if state==0:
            soft=k<HARD_THRESHOLD
            category=(20 if soft else 18)+(0 if single else 1)
            stride=(80 if soft else 64)+(0 if single else 16)
            count_offset=0xa4+4*category;count=u32(count_offset)
            row=u32(0x16c)+16*((u32(0x40+4*category)+count*(stride//16))&0xffffffff)
            if row+stride>len(context):raise ValueError('Complete retained angular row required')
            args=dict(class_byte=int(single),base_row=u32(0x40+4*category),class_count=count,
                row_region_offset=u32(0x16c),result_count=u32(0x180),context_scalar=struct.unpack_from('<f',context,0xc)[0],
                context_flags=u32(0x38),axis=axis,reference=reference,target=target,atan2=atan2)
            built=(build_soft_pose_row(bytes(context[row:row+stride]),stiffness=[k]*4,damping=[d]*4,**args)
                   if soft else build_hard_pose_row(bytes(context[row:row+stride]),**args))
            context[row:row+stride]=built['row']
            struct.pack_into('<I',context,count_offset,built['next_class_count'])
            struct.pack_into('<I',context,0x180,built['next_result_count'])
            struct.pack_into('<HH',context,row,*indices)
        else:
            angle=pose_row_angle(axis,reference,target,atan2)['angle']
            for sign,bound in ((-1.,hi),(1.,-lo)):
                row=build_pose_angular_limit_row(context,single=single,axis=axis,coordinate=[angle]*4,
                    sign=[sign]*4,offset=[bound]*4,response_term=[HARD_THRESHOLD]*4,response_mix=[0.]*4)
                struct.pack_into('<HH',context,row,*indices)


def build_pose_axis_constraint(context,constraint,*,bodies,metadata,atan2,notify=None):
    """Complete kind2 translation, angular and optional direct-drive composition.

    Axis constraint is an authored name. Atan2 and reached body notifications
    remain explicit services; callback mutation is outside validation coverage.
    """
    from .pose_constraint_drive import build_pose_angular_drive_row
    data=build_pose_axis_translations(context,constraint,bodies=bodies,metadata=metadata)
    build_pose_axis_angular_rows(context,constraint,prepared=data,atan2=atan2)
    config=data['config']
    for i,(state_offset,drive_offset) in enumerate(zip((0xbc,0xd0,0xe4),(0xf8,0x104,0x110))):
        state=struct.unpack_from('<I',config,state_offset)[0]
        if state==0 or not config[drive_offset]:continue
        sample,strength=struct.unpack_from('<2f',config,drive_offset+4)
        axis=data['axes'][int(bool(constraint[0x59]))][i]
        row=build_pose_angular_drive_row(context,single=data['single'],mode=2,
            axis=axis,sample=[sample]*4,impulse_bound=[strength]*4)
        struct.pack_into('<HH',context,row,*data['body_indices'])
        if not config[drive_offset+1]:
            token=struct.unpack_from('<Q',constraint,8)[0];body=bodies[token]
            if struct.unpack_from('<Q',body,0x10)[0] and struct.unpack_from('<Q',metadata[struct.unpack_from('<Q',body,0x30)[0]],0x20)[0]:
                if notify is None:raise ValueError('Reached kind2 notification requires service')
                notify(token,2)
    return 1
