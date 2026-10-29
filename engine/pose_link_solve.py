"""Connected primary/tangent slice of recovered solver traversal.

Evidence: LINK_SOLVER.md, Connected primary and tangent solver slice.
"""
import struct
from .pose_point_solver import prepare_pose_point_row,iterate_pose_point_row
from .pose_paired_point_solver import prepare_pose_paired_point_row,iterate_pose_paired_point_row
from .pose_angular_solver import prepare_pose_angular_row,iterate_pose_angular_row
from .pose_paired_angular_solver import prepare_pose_paired_angular_row,iterate_pose_paired_angular_row
from .pose_command_solver import prepare_pose_command_row,iterate_pose_command_row
from .pose_shared_solver import prepare_pose_shared_row,iterate_pose_shared_row
from .pose_paired_shared_solver import prepare_pose_paired_shared_row,iterate_pose_paired_shared_row
from .pose_solver_control import run_pose_solver
from .pose_primary_solver import prepare_pose_primary_row,iterate_pose_primary_row
from .pose_paired_primary_solver import prepare_pose_paired_primary_row,iterate_pose_paired_primary_row
from .pose_paired_tangent_solver import prepare_pose_paired_tangent_row,iterate_pose_paired_tangent_row
from .pose_tangent_solver import prepare_pose_tangent_row,iterate_pose_tangent_row


def solve_pose_link_rows(context_bytes, *, base_token, primary_rows, secondary_rows,
                         body_data, body_state, results, paired_primary_rows=(), paired_tangent_rows=(),
                         shared_rows=(), paired_shared_rows=(), command_rows=(), angular_rows=(), paired_angular_rows=(), constraint_primary_rows=(), paired_constraint_primary_rows=(), point_rows=(), paired_point_rows=(), arena=None):
    """Run native phase/count policy for the thirteen supported row categories.

    Traversal counts come from context108/120, not builder append counters.
    Other row-category counts must be zero. The caller supplies already populated
    rows, retained body data/state and result storage; no count producer is guessed.
    """
    if len(context_bytes)<0x17c:raise ValueError('Complete solver context fields required')
    counts=struct.unpack_from('<25I',context_bytes,0x108)
    if any(value for i,value in enumerate(counts) if i not in (0,1,4,5,6,7,8,9,10,11,12,13,24)):
        raise ValueError('Unsupported populated row category')
    primary_count,paired_count,secondary_count=counts[0],counts[1],counts[6]
    if primary_count>len(primary_rows) or paired_count>len(paired_primary_rows) or secondary_count>len(secondary_rows):
        raise ValueError('Insufficient retained solver rows')
    paired_tangent_count=counts[7]
    if paired_tangent_count>len(paired_tangent_rows):raise ValueError('Insufficient retained paired tangent rows')
    shared_count,paired_shared_count=counts[4],counts[5]
    if shared_count>len(shared_rows) or paired_shared_count>len(paired_shared_rows):
        raise ValueError('Insufficient retained shared rows')
    command_count=counts[24]
    if command_count>len(command_rows):raise ValueError('Insufficient retained command rows')
    angular_count,paired_angular_count=counts[12],counts[13]
    if angular_count>len(angular_rows) or paired_angular_count>len(paired_angular_rows):
        raise ValueError('Insufficient retained angular rows')
    constraint_count,paired_constraint_count=counts[8],counts[9]
    if constraint_count>len(constraint_primary_rows) or paired_constraint_count>len(paired_constraint_primary_rows):
        raise ValueError('Insufficient retained constraint primary rows')
    point_count,paired_point_count=counts[10],counts[11]
    if point_count>len(point_rows) or paired_point_count>len(paired_point_rows):
        raise ValueError('Insufficient retained point rows')
    def location(category,index,stride):
        if arena is None:return {}
        start=struct.unpack_from('<I',context_bytes,0x16c)[0]+16*struct.unpack_from('<I',context_bytes,0x40+4*category)[0]
        return dict(arena=arena,row_offset=start+index*stride)
    args=dict(body_data=body_data,body_state=body_state,results=results)
    def prepare(descriptor,cursor):
        if not descriptor['special']:
            for row in command_rows[:command_count]:
                prepare_pose_command_row(row,body_data=body_data,body_state=body_state)
            for row in paired_angular_rows[:paired_angular_count]:prepare_pose_paired_angular_row(row,**args)
            for row in angular_rows[:angular_count]:prepare_pose_angular_row(row,**args)
            for row in paired_constraint_primary_rows[:paired_constraint_count]:prepare_pose_paired_primary_row(row,**args)
            for row in constraint_primary_rows[:constraint_count]:prepare_pose_primary_row(row,**args)
            for row in paired_point_rows[:paired_point_count]:prepare_pose_paired_point_row(row,**args)
            for row in point_rows[:point_count]:prepare_pose_point_row(row,**args)
        for row in paired_primary_rows[:paired_count]:prepare_pose_paired_primary_row(row,**args)
        for row in primary_rows[:primary_count]:prepare_pose_primary_row(row,**args)
        if not descriptor['special']:
            for row in paired_shared_rows[:paired_shared_count]:prepare_pose_paired_shared_row(row,**args)
            for row in shared_rows[:shared_count]:prepare_pose_shared_row(row,**args)
            for row in paired_tangent_rows[:paired_tangent_count]:prepare_pose_paired_tangent_row(row,**args)
            for row in secondary_rows[:secondary_count]:prepare_pose_tangent_row(row,**args)
    def iterate(descriptor,cursor):
        if not descriptor['special']:
            for row in command_rows[:command_count]:
                iterate_pose_command_row(row,body_data=body_data,body_state=body_state)
            for row in paired_angular_rows[:paired_angular_count]:iterate_pose_paired_angular_row(row,**args)
            for row in angular_rows[:angular_count]:iterate_pose_angular_row(row,**args)
            for i,row in enumerate(paired_constraint_primary_rows[:paired_constraint_count]):iterate_pose_paired_primary_row(row,**args,**location(9,i,128))
            for i,row in enumerate(constraint_primary_rows[:constraint_count]):iterate_pose_primary_row(row,**args,**location(8,i,112))
            for row in paired_point_rows[:paired_point_count]:iterate_pose_paired_point_row(row,**args)
            for row in point_rows[:point_count]:iterate_pose_point_row(row,**args)
        for i,row in enumerate(paired_primary_rows[:paired_count]):iterate_pose_paired_primary_row(row,**args,**location(1,i,128))
        for i,row in enumerate(primary_rows[:primary_count]):iterate_pose_primary_row(row,**args,**location(0,i,112))
        if not descriptor['special']:
            for row in paired_shared_rows[:paired_shared_count]:iterate_pose_paired_shared_row(row,**args)
            for row in shared_rows[:shared_count]:iterate_pose_shared_row(row,**args)
            for row in paired_tangent_rows[:paired_tangent_count]:iterate_pose_paired_tangent_row(row,**args)
            for row in secondary_rows[:secondary_count]:iterate_pose_tangent_row(row,**args)
    run_pose_solver(context_bytes,base_token=base_token,prepare=prepare,iterate=iterate)
