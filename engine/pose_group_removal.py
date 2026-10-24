"""Recovered context group-list removal, without group destruction.

Evidence: CENTRAL_IMPULSE.md, Context group removal.
"""


def remove_pose_group(context, group, *, groups):
    """Swap-remove from flag-selected list; preserve removed object's fields.

    Valid retained membership is checked as an authored guard. No destructor,
    index invalidation, flag clearing or resource release occurs in this helper.
    """
    array=context['groups428' if group['flag_a0'] else 'groups418']
    index=group['index'];count=array['count'];slots=array['slots']
    if not 0<=index<count<=len(slots) or slots[index]!=group['token']:
        raise ValueError('Valid retained group membership required')
    array['count']=count-1
    slots[index]=slots[count-1]
    if index<count-1:groups[slots[index]]['index']=index
