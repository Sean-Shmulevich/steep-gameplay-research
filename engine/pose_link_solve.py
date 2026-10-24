"""Connected primary/tangent slice of recovered solver traversal.

Evidence: CENTRAL_IMPULSE.md, Connected primary and tangent solver slice.
"""
import struct
from .pose_solver_control import run_pose_solver
from .pose_primary_solver import prepare_pose_primary_row,iterate_pose_primary_row
from .pose_tangent_solver import prepare_pose_tangent_row,iterate_pose_tangent_row


def solve_pose_link_rows(context_bytes, *, base_token, primary_rows, secondary_rows,
                         body_data, body_state, results):
    """Run native phase/count policy for the two supported row categories.

    Traversal counts come from context108/120, not builder append counters.
    Other row-category counts must be zero. The caller supplies already populated
    rows, retained body data/state and result storage; no count producer is guessed.
    """
    if len(context_bytes)<0x17c:raise ValueError('Complete solver context fields required')
    counts=struct.unpack_from('<25I',context_bytes,0x108)
    if any(value for i,value in enumerate(counts) if i not in (0,6)):
        raise ValueError('Unsupported populated row category')
    primary_count,secondary_count=counts[0],counts[6]
    if primary_count>len(primary_rows) or secondary_count>len(secondary_rows):
        raise ValueError('Insufficient retained solver rows')
    args=dict(body_data=body_data,body_state=body_state,results=results)
    def prepare(descriptor,cursor):
        for row in primary_rows[:primary_count]:prepare_pose_primary_row(row,**args)
        if not descriptor['special']:
            for row in secondary_rows[:secondary_count]:prepare_pose_tangent_row(row,**args)
    def iterate(descriptor,cursor):
        for row in primary_rows[:primary_count]:iterate_pose_primary_row(row,**args)
        if not descriptor['special']:
            for row in secondary_rows[:secondary_count]:iterate_pose_tangent_row(row,**args)
    run_pose_solver(context_bytes,base_token=base_token,prepare=prepare,iterate=iterate)
