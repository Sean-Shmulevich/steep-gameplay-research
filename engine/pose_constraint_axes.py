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
