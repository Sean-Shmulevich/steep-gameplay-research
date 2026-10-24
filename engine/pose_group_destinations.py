"""Recovered multi-body group destination selection.

Evidence: CENTRAL_IMPULSE.md, Multi-body destination assignment.
"""


def assign_pose_group_destinations(context, group, destinations, *, count,
                                   preparation_result, eligible, acquire_group,
                                   resolve_body=lambda body: body):
    """Fill null entries in place; preserve seeded destinations.

    Group slots are read each iteration. Eligibility and acquisition are supplied;
    no body migration or group destruction occurs in this selection loop.
    """
    if type(preparation_result) is not int or not 0<=preparation_result<=0xffffffff:
        raise ValueError('Raw uint32 preparation result required')
    if type(count) is not int or not 0<=count<=len(destinations):
        raise ValueError('Retained destination count required')
    reuse_available=(preparation_result==0)
    for index in range(count):
        if destinations[index]:continue
        body=resolve_body(group['slots'][index])
        if body['metadata']['flags8']&8 and eligible(context,body)&255:
            destinations[index]=context['group410']
        elif reuse_available:
            destinations[index]=group['token'];reuse_available=False
        else:
            destinations[index]=acquire_group(context)
    return reuse_available
