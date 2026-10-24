"""Recovered ordinary-group finalization and context-list transfer.

Evidence: CENTRAL_IMPULSE.md, Ordinary-group finalization.
"""


def finalize_pose_group(context, group, *, groups, bodies, links, virtual40, grow):
    """Serial normal-return flow with retained storage and external callbacks.

    Context arrays: groups418, groups428, tracked, pending_links.
    Group: token,index,flag_a0,count,slots,link_count,link_slots.
    """
    if not group['flag_a0'] or group['token'] in (context['group408'],context['group410']):
        return False
    def append(array,value):
        if array['count']==array['capacity']:
            grow(array,8 if array['capacity']==0 else (array['capacity']*2)&0xffffffff)
        i=array['count']
        if not 0<=i<len(array['slots']):raise ValueError('Writable retained array required')
        array['slots'][i]=value() if callable(value) else value;array['count']=(i+1)&0xffffffff
    slots=group['link_slots'];count=group['link_count']
    for i in range(count):
        link=links[slots[i]]
        if bodies[link['first']]['metadata']['kind8']&15==2:
            # The native caller reloads this slot after possible growth.
            append(context['pending_links'],lambda:slots[i])
    slots=group['slots'];count=group['count']
    for i in range(count):virtual40(bodies[slots[i]])
    group['flag_a0']=0
    source=context['groups428'];index=group['index']
    source['count']-=1;n=source['count'];source['slots'][index]=source['slots'][n]
    if index<n:groups[source['slots'][index]]['index']=index
    target=context['groups418'];group['index']=target['count']
    append(target,group['token'])
    # Native helper captures group count and tracked count before growth.
    tracked=context['tracked'];count=group['count'];old=tracked['count'];needed=(old+count)&0xffffffff
    capacity=tracked['capacity']
    if needed>capacity:
        if capacity:
            while capacity<needed:
                capacity=(capacity*2)&0xffffffff
                if capacity==0:raise ValueError('Capacity growth wrapped')
        else:capacity=needed
        grow(tracked,capacity)
    tracked['count']=needed
    for i in range(count):tracked['slots'][old+i]=group['slots'][i]
    return True
