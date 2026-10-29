"""Composed retained-storage preparation before group solve entry.

Evidence: LINK_SOLVER.md, Group preparation through solve entry.
"""
import struct
from .pose_category_counts import count_pose_categories
from .pose_link_counts import count_pose_link_rows
from .pose_solver_layout import initialize_pose_solver_storage
from .pose_solver_settings import initialize_pose_solver_settings


def prepare_pose_group(context, settings, *, scalar, group_token, body_count,
                       link_tokens, pose_tokens, links, payloads, poses, bodies):
    """Count, lay out and configure a caller-owned retained solver allocation.

    Object dictionaries are explicit stable views used by the recovered counters.
    The caller supplies sufficient storage; allocation/release and the subsequent
    group step remain separate. No eligibility filtering or count repair is added.
    Return the authored layout description, not a native function return value.
    """
    counts=[0]*25
    mode=struct.unpack_from('<I',settings,0x24)[0]
    count_pose_link_rows(counts,link_tokens,links=links,bodies=bodies,
                         payloads=payloads,mode=mode)
    count_pose_categories(counts,pose_tokens,poses=poses,bodies=bodies)
    plan=initialize_pose_solver_storage(context,counts,body_count)
    initialize_pose_solver_settings(context,settings,scalar=scalar,group_token=group_token)
    return plan
