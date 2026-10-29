"""Retained record views and one-pass composition for reconstructed pose groups.

Evidence: LINK_SOLVER.md, Repeated retained group passes.
"""
import struct
from .pose_group_prepare import prepare_pose_group
from .pose_group_runtime import run_pose_group_runtime
from .pose_link_runtime import make_pose_link_services


def read_retained_pose_group(group, *, arrays, bodies, metadata, links,
                             entry_arrays, constraints, get_kind):
    """Read current active spans and fields; no cached counts or live-memory reads.

    Inputs must be stable, well-formed retained records. Eager parsing is authored
    adapter policy, not native access ordering or an atomic snapshot guarantee.
    """
    def span(offset):
        pointer,count=struct.unpack_from('<QI',group,offset)
        if not count:return []
        values=arrays[pointer]
        if len(values)<count:raise ValueError('Complete active pointer span required')
        return list(values[:count])
    body_tokens,link_tokens,pose_tokens=(span(off) for off in (0x10,0x40,0x90))
    parsed_links={};parsed_poses={};needed=set(body_tokens)
    for token in link_tokens:
        raw=links[token];first,second=struct.unpack_from('<2Q',raw,8)
        pointer,count=struct.unpack_from('<QI',raw,0x58)
        entries=entry_arrays[pointer] if count else b''
        if len(entries)<16*count:raise ValueError('Complete active contact entries required')
        parsed_links[token]=dict(flags84=raw[0x84],first_body=first,second_body=second,
            payload_count=count,payload_slots=[struct.unpack_from('<Q',entries,16*i+8)[0] for i in range(count)])
        needed.update((first,second))
    for token in pose_tokens:
        raw=constraints[token];first,second=struct.unpack_from('<2Q',raw,8)
        parsed_poses[token]=dict(type=get_kind(token),second_body=second,storage70=bytes(raw[0x70:]))
        if parsed_poses[token]['type']==2:parsed_poses[token]['storage70']=bytes(raw[0x70:0x190])
        needed.update((first,second))
    parsed_bodies={}
    for token in needed-{0}:
        raw=bodies[token];meta=metadata[struct.unpack_from('<Q',raw,0x30)[0]]
        pointer=struct.unpack_from('<Q',raw,0xb8)[0];count=struct.unpack_from('<H',raw,0xc0)[0]
        entries=entry_arrays[pointer] if count else b''
        if len(entries)<72*count:raise ValueError('Complete active body resource entries required')
        v=lambda offset:list(struct.unpack_from('<3f',raw,offset))
        parsed_bodies[token]=dict(frame=dict(basis=[v(o) for o in (0x40,0x50,0x60)],translation=v(0x70)),
            offset128=v(0x128),motion1a0=v(0x1a0),motion1ac=v(0x1ac),
            index1c=struct.unpack_from('<H',raw,0x1c)[0],metadata_flags50=struct.unpack_from('<H',meta,0x50)[0],
            entries=[struct.unpack_from('<Q',entries,72*i+16)[0] for i in range(count)])
    return dict(body_tokens=body_tokens,link_tokens=link_tokens,pose_tokens=pose_tokens,
                bodies=parsed_bodies,links=parsed_links,poses=parsed_poses)


def run_retained_pose_group_pass(arena, settings, *, scalar, group_token, base_token,
                                 groups, arrays, bodies, metadata, links, entry_arrays,
                                 constraints, get_kind, payloads, resources, profiles,
                                 modes, poststep, atan2=None, notify=None,
                                 damping_records=None, damping_response=None,
                                 update_body=None):
    """Rebuild views and execute preparation plus one joined group pass.

    No scheduler admission, contact generation, allocation growth, reactivation or
    fixed timestep is invented. Caller-owned capacity and all reached services are
    required. Each invocation reads current raw counts, frames and motion anew.
    """
    group=groups[group_token]
    parsed=read_retained_pose_group(group,arrays=arrays,bodies=bodies,metadata=metadata,
        links=links,entry_arrays=entry_arrays,constraints=constraints,get_kind=get_kind)
    plan=prepare_pose_group(arena,settings,scalar=scalar,group_token=group_token,
        body_count=struct.unpack_from('<I',group,0x18)[0],link_tokens=parsed['link_tokens'],
        pose_tokens=parsed['pose_tokens'],links=parsed['links'],payloads=payloads,
        poses=parsed['poses'],bodies=parsed['bodies'])
    services=make_pose_link_services(arena,arrays=arrays,links=parsed['links'],
        bodies=parsed['bodies'],payloads=payloads,resources=resources,profiles=profiles,modes=modes)
    run_pose_group_runtime(arena,base_token=base_token,groups=groups,arrays=arrays,
        bodies=bodies,metadata=metadata,constraints=constraints,get_kind=get_kind,
        link_services=services,poststep=poststep,atan2=atan2,notify=notify,
        damping_records=damping_records,damping_response=damping_response,update_body=update_body)
    return plan
