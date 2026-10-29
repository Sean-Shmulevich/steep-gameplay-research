"""Recovered poststep quiet aggregation and body inactive transition.

Evidence: LINK_SOLVER.md, Group quiet aggregation and poststep integration gate.
"""
import struct
from .pose_body_quiet_state import update_pose_body_quiet_state


def transition_pose_body_inactive(token, body, metadata, *, links, clear_link):
    """Constructor-selected slot20: mark state2, zero motion, clear linked payloads.

    links maps opaque identities to retained raw link headers. clear_link(token)
    supplies payload clearing/release. Broken ring detection is an authored error,
    after reached side effects, not native rollback behavior.
    """
    if len(body)<0x1b8 or len(metadata)<0x54:raise ValueError('Retained body/metadata required')
    metadata[0x53]=(metadata[0x53]&0xf2)|2
    body[0x1a0:0x1b8]=bytes(24)
    first=struct.unpack_from('<Q',body,0x80)[0]
    current=first;seen=set()
    while current:
        if current in seen:raise ValueError('Malformed retained link ring')
        seen.add(current)
        clear_link(current)
        link=links[current]
        endpoint=struct.unpack_from('<Q',link,8)[0]
        current=struct.unpack_from('<Q',link,0x20 if endpoint==token else 0x30)[0]
        if current==first:return
        if not current:raise ValueError('Nonempty link ring ended at null')


def check_pose_group_quiet(group, *, bodies, scalar, duration_threshold,
                           linear_threshold, angular_threshold, set_inactive):
    """Update every captured body; transition a reloaded span if all report1.

    bodies[token] supplies storage, metadata and optional overrides. Array count
    and list identity are captured per traversal. Failed aggregation leaves the
    existing group flag untouched; an empty group passes aggregation.
    """
    slots,count=group['slots'],group['count'];all_quiet=True
    for i in range(count):
        token=slots[i];record=bodies[token]
        update_pose_body_quiet_state(record['storage'],record['metadata'],scalar=scalar,
            duration_threshold=duration_threshold,linear_threshold=linear_threshold,
            angular_threshold=angular_threshold,overrides=record.get('overrides'))
        if all_quiet and record['metadata'][0x53]&15!=1:all_quiet=False
    if all_quiet:
        slots,count=group['slots'],group['count']
        for i in range(count):set_inactive(slots[i])
        group['flag_a0']=1


def poststep_pose_group(group, *, bodies, scalar, check_enabled,
                        duration_threshold, linear_threshold, angular_threshold,
                        set_inactive, integrate, refresh):
    """Run optional quiet check, then integration and resource refresh if active.

    Callbacks are required services. This function does not assume every body
    class has the constructor-selected inactive method, or supply resource refresh.
    """
    if check_enabled:
        check_pose_group_quiet(group,bodies=bodies,scalar=scalar,
            duration_threshold=duration_threshold,linear_threshold=linear_threshold,
            angular_threshold=angular_threshold,set_inactive=set_inactive)
    if group['flag_a0']:return
    slots,count=group['slots'],group['count']
    for i in range(count):integrate(slots[i],scalar)
    slots,count=group['slots'],group['count']
    for i in range(count):refresh(slots[i])


def poststep_integrated_pose_group(group, *, bodies, scalar, check_enabled,
                                  duration_threshold, linear_threshold,
                                  angular_threshold, links, clear_link,
                                  entry_arrays, transforms, metadata,
                                  resource_bounds, half_angle_trig):
    """Compose poststep for the recovered constructor-selected body class.

    Evidence: LINK_SOLVER.md, Integrated group poststep. Body records retain the
    quiet-check metadata view; metadata maps identities used by bounds refresh.
    These must reference the same storage when their native identities coincide.
    Resource bounds, link release and trig are explicit services. Mutations are
    in place, with no rollback; this does not provide concurrent lifetime safety.
    """
    from .pose_body_integration import integrate_pose_body
    from .pose_body_bounds import refresh_pose_body_bounds

    def inactive(token):
        record = bodies[token]
        transition_pose_body_inactive(token, record['storage'], record['metadata'],
                                      links=links, clear_link=clear_link)

    def integrate(token, step):
        integrate_pose_body(bodies[token]['storage'], step,
                            half_angle_trig=half_angle_trig)

    def refresh(token):
        refresh_pose_body_bounds(bodies[token]['storage'], entry_arrays=entry_arrays,
                                 transforms=transforms, metadata=metadata,
                                 resource_bounds=resource_bounds)

    poststep_pose_group(group, bodies=bodies, scalar=scalar,
                       check_enabled=check_enabled,
                       duration_threshold=duration_threshold,
                       linear_threshold=linear_threshold,
                       angular_threshold=angular_threshold,
                       set_inactive=inactive, integrate=integrate, refresh=refresh)
