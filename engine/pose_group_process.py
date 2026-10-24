"""Recovered ordinary-group processing with retained storage and explicit services.

Evidence: CENTRAL_IMPULSE.md, Ordinary-group processing and retirement.
"""
from .pose_group_destinations import assign_pose_group_destinations


def process_pose_group(context, group, *, bodies, finalize, eligible,
                       remove_body, append_body, allocate, prepare, acquire_group,
                       migrate, release, remove_group, destroy):
    """Return whether the normal path invoked removal and destruction.

    Slots contain body tokens resolved through bodies. allocate(bytes) returns a
    writable destination list; prepare(context, group, descriptor) seeds it and
    returns a component count. migrate(group, descriptor) mutates its count.
    Storage and all callback effects remain caller-owned. No exception cleanup
    or native lifetime guarantee is invented.
    """
    finalize(context, group)
    count=group['count']
    if count==1:
        body=bodies[group['slots'][0]]
        if not body['metadata']['flags8']&8 or not eligible(context,body)&255:
            return False
        remove_body(group,body)
        append_body(context['group410'],body)  # Native ignores append's return.
    elif count>1:
        storage=allocate((count*8)&0xffffffff)
        descriptor=dict(slots=storage,count=count)
        components=prepare(context,group,descriptor)
        reuse=assign_pose_group_destinations(
            context,group,storage,count=count,preparation_result=components,
            eligible=eligible,acquire_group=acquire_group,
            resolve_body=bodies.__getitem__)
        # The caller reconstructs the descriptor before migration.
        descriptor=dict(slots=storage,count=count)
        migrate(group,descriptor)
        release(storage)
        if not reuse:
            return False
    remove_group(context,group)
    destroy(group,1)
    return True
