"""Group-step composition with explicit link, damping and poststep services.

Evidence: LINK_SOLVER.md, Joined group numerical runtime.
"""
import struct
from .pose_body_buffers import build_pose_body_buffers
from .pose_body_feedback import write_pose_body_feedback
from .pose_body_secondary_update import apply_pose_secondary_body_state
from .pose_constraint_build import build_pose_constraints
from .pose_constraint_feedback import feedback_pose_constraints
from .pose_group_step import run_pose_group_step
from .pose_solver_arena import solve_pose_arena


def run_pose_group_runtime(context, *, base_token, groups, arrays, bodies, metadata,
                           constraints, get_kind, link_services, poststep,
                           atan2=None, notify=None, damping_records=None,
                           damping_response=None, update_body=None):
    """Join body production, pose construction, solving and feedback in native order.

    groups/bodies/metadata/constraints contain retained raw records. arrays maps
    exact array-base tokens to ordered identity lists. Reached link operations and
    poststep remain mandatory services. Damping records map native-shaped tokens
    to four floats. Native ownership, concurrent mutation and allocation are absent.
    """
    view=memoryview(context)
    def tokens(start,end):
        if end<start or (end-start)%8:raise ValueError('Whole retained pointer span required')
        count=(end-start)//8
        if not count:return []
        values=arrays[start]
        if len(values)<count:raise ValueError('Complete retained pointer array required')
        return values[:count]
    def records(offset,count,stride):
        if offset<0x190 or offset+count*stride>len(context):
            raise ValueError('Complete arena body range required')
        return [view[offset+i*stride:offset+(i+1)*stride] for i in range(count)]
    def state(count):
        return records(struct.unpack_from('<I',context,0x174)[0],count,32)
    def build_bodies(data_ptr,state_ptr,start,count,scalar_ptr,vector_ptr):
        ordered=[]
        for token in tokens(start,start+count*8):
            body=bodies[token];meta=metadata[struct.unpack_from('<Q',body,0x30)[0]]
            v=lambda offset:list(struct.unpack_from('<3f',body,offset))
            damp=struct.unpack_from('<Q',body,0x1b8)[0]
            # Fixed bodies and zero scalar bypass damping record reads natively.
            scalar=struct.unpack_from('<f',context,scalar_ptr-base_token)[0]
            damping=None
            if damp and scalar!=0 and not meta[0x52]&8:
                if damping_records is None:raise ValueError('Reached damping record required')
                damping=damping_records[damp]
            ordered.append(dict(metadata_flags52=meta[0x52],flagsaa=body[0xaa],
                basis=[v(o) for o in (0x40,0x50,0x60)],
                tensor170=[v(o) for o in (0x170,0x180,0x190)],
                motion1a0=v(0x1a0),motion1ac=v(0x1ac),
                scalar124=struct.unpack_from('<f',body,0x124)[0],damping1b8=damping))
        produced=build_pose_body_buffers(ordered,
            scalar=struct.unpack_from('<f',context,scalar_ptr-base_token)[0],
            vector=struct.unpack_from('<3f',context,vector_ptr-base_token),
            damping_response=damping_response)
        for name,ptr,stride in (('body_data',data_ptr,64),('body_state',state_ptr,32)):
            for target,source in zip(records(ptr-base_token,count,stride),produced[name]):target[:]=source
    def build_constraints(_,start,end):
        build_pose_constraints(context,tokens(start,end),constraints=constraints,
            bodies=bodies,metadata=metadata,get_kind=get_kind,atan2=atan2,notify=notify)
    def body_feedback(_,start,end):
        selected=tokens(start,end)
        write_pose_body_feedback(selected,bodies=bodies,body_state=state(len(selected)))
    def pose_feedback(_,start,end):
        feedback_pose_constraints(context,tokens(start,end),constraints=constraints,
            bodies=bodies,metadata=metadata,get_kind=get_kind)
    def secondary(_,start,end):
        if update_body is None:raise ValueError('Reached secondary body update requires service')
        selected=tokens(start,end)
        apply_pose_secondary_body_state(selected,bodies=bodies,body_state=state(len(selected)),update_body=update_body)
    services=dict(build_body_buffers=build_bodies,build_pose_rows=build_constraints,
                  solve=lambda _:solve_pose_arena(context,base_token=base_token),
                  body_feedback=body_feedback,pose_feedback=pose_feedback,
                  apply_secondary_state=secondary,poststep=poststep)
    for name in ('build_link_rows','link_feedback','refresh_secondary_rows'):
        services[name]=link_services[name]
    run_pose_group_step(context,base_token=base_token,groups=groups,services=services)
