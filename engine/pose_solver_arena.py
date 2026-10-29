"""Retained-arena adapter for the reconstructed 25-category numerical solver.

Evidence: LINK_SOLVER.md, Complete arena numerical dispatch.
"""
import struct
from .pose_solver_layout import STRIDE_UNITS
from .pose_link_solve import solve_pose_link_rows

CATEGORY_ARGUMENTS=(
    'primary_rows','paired_primary_rows','late_primary_rows','paired_late_primary_rows',
    'shared_rows','paired_shared_rows','secondary_rows','paired_tangent_rows',
    'constraint_primary_rows','paired_constraint_primary_rows','point_rows','paired_point_rows',
    'angular_rows','paired_angular_rows','plain_bounded_rows','paired_plain_bounded_rows',
    'bounded_rows','paired_bounded_rows','axis_angular_rows','paired_axis_angular_rows',
    'softened_axis_rows','paired_softened_axis_rows','two_stage_rows','paired_two_stage_rows',
    'command_rows')


def solve_pose_arena(arena, *, base_token=0):
    """Solve directly in retained storage, including cross-row result references.

    Layout and rows must already be prepared. Native traversal uses planned counts,
    not append counters. This adapter adds bounds checks, not count reconciliation.
    It preserves unused bytes and aliases body/result records into the same arena.
    """
    if len(arena)<0x190:raise ValueError('Complete retained arena required')
    view=memoryview(arena)
    word=lambda off:struct.unpack_from('<I',arena,off)[0]
    def records(start,count,stride):
        if start<0x190 or start+count*stride>len(arena):
            raise ValueError('Complete retained record range required')
        return [view[start+i*stride:start+(i+1)*stride] for i in range(count)]
    counts=struct.unpack_from('<25I',arena,0x108)
    rows={name:records(word(0x16c)+16*word(0x40+4*i),counts[i],16*STRIDE_UNITS[i])
          for i,name in enumerate(CATEGORY_ARGUMENTS)}
    data,state,result=(word(off) for off in (0x170,0x174,0x178))
    if state<data or result<state or (state-data)%64 or (result-state)%32:
        raise ValueError('Ordered whole body-buffer records required')
    solve_pose_link_rows(arena,base_token=base_token,arena=arena,
        body_data=records(data,(state-data)//64,64),
        body_state=records(state,(result-state)//32,32),
        results=records(result,sum(counts),16),**rows)
