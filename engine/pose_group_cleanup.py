"""Recovered group storage cleanup, without freeing the group object itself.

Evidence: CENTRAL_IMPULSE.md, Group destructor storage cleanup.
"""


def cleanup_pose_group(group, *, group_table, base_table, release, allocate_zero):
    """Mutate retained storage descriptors in native order.

    bodies/links: pointer, inline, count, capacity. poses: pointer/count/capacity.
    Tokens are supplied identities, not addresses this module dereferences.
    release(pointer) and allocate_zero(0,16,55) supply allocator virtual effects.
    The unusual null pose pointer/nonzero capacity path is preserved explicitly.
    """
    group['table']=group_table
    poses=group['poses']
    if poses['capacity']:
        pointer=poses['pointer']
        if pointer:
            release(pointer)
            poses['pointer']=0
        else:
            poses['pointer']=allocate_zero(0,16,55)
        poses['capacity']=0
        if poses['count']>0:poses['count']=0
    for family,inline_capacity in (('links',8),('bodies',4)):
        storage=group[family]
        if storage['capacity']:
            if storage['pointer']!=storage['inline']:
                release(storage['pointer'])
                storage['pointer']=storage['inline']
            storage['capacity']=inline_capacity
            storage['pointer']=0
            if storage['count']>0:
                storage['count']=0
                storage['capacity']=0
            else:
                storage['capacity']=0
        else:
            storage['pointer']=0
            storage['capacity']=0
    group['table']=base_table
