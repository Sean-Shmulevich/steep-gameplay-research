"""Retained-record adapter for constructor-selected integrated group poststep.

Evidence: LINK_SOLVER.md, Joined secondary correction and poststep.
"""
import struct
from .pose_group_poststep import poststep_integrated_pose_group


def make_integrated_pose_poststep(*, groups, arrays, bodies, metadata, links,
                                  clear_link, entry_arrays, transforms,
                                  resource_bounds, half_angle_trig,
                                  quiet_overrides=None):
    """Bind the known body implementation, not arbitrary virtual body classes.

    Maps describe stable retained records. Nonzero body1c0 requires an explicit
    override record when quiet checking is reached. Allocation, live ownership and
    callback-driven group membership replacement are outside this adapter.
    """
    def poststep(group_token,scalar,enabled,duration,linear,angular):
        raw_group=groups[group_token]
        start,count=struct.unpack_from('<QI',raw_group,0x10)
        slots=arrays[start] if count else []
        if len(slots)<count:raise ValueError('Complete retained group membership required')
        group=dict(slots=slots,count=count,flag_a0=raw_group[0xa0])
        records={}
        for token in slots[:count]:
            body=bodies[token]
            records[token]=dict(storage=body,metadata=metadata[struct.unpack_from('<Q',body,0x30)[0]])
            if enabled:
                override=struct.unpack_from('<Q',body,0x1c0)[0]
                if override:
                    if quiet_overrides is None:raise ValueError('Reached quiet override record required')
                    records[token]['overrides']=quiet_overrides[override]
        try:
            poststep_integrated_pose_group(group,bodies=records,scalar=scalar,
                check_enabled=enabled,duration_threshold=duration,
                linear_threshold=linear,angular_threshold=angular,links=links,
                clear_link=clear_link,entry_arrays=entry_arrays,transforms=transforms,
                metadata=metadata,resource_bounds=resource_bounds,half_angle_trig=half_angle_trig)
        finally:
            raw_group[0xa0]=group['flag_a0']
    return poststep
