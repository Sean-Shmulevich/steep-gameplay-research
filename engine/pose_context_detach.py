"""Recovered context-level body detach ordering.

Evidence: CENTRAL_IMPULSE.md, Context body detach.
Service effects and retained array lifetime remain external.
"""


def detach_pose_body(context, body, *, remove_body, prune_constraints,
                     process_group):
    """Capture old group, remove locally, perform group-specific cleanup.

    Arrays use {count,slots}; slots remain retained during traversal. Counts and
    list identities are captured once per array, values read on each iteration.
    """
    old_group=body['group']
    remove_body(old_group,body)
    if old_group==context['group408']:
        for name in ('groups418','groups428'):
            array=context[name];slots=array['slots'];count=array['count']
            if not 0<=count<=len(slots):raise ValueError('Retained array bounds required')
            for index in range(count):prune_constraints(slots[index],body)
    elif old_group!=context['group410']:
        process_group(context,old_group)
    tracked=context['tracked'];count=tracked['count'];slots=tracked['slots']
    if not 0<=count<=len(slots):raise ValueError('Retained tracked array required')
    for index in range(count):
        if slots[index]==body['token']:
            slots[index]=slots[count-1];tracked['count']=(count-1)&0xffffffff
            return index
    return None
