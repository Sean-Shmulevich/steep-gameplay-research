"""Recovered group body append, separate from pose-record attachment.

Evidence: CENTRAL_IMPULSE.md, Body group append.
"""


def append_pose_body(group, body, *, grow):
    """Publish membership before capacity growth, then reload insertion count.

    group: token,count,capacity,slots; body: token,flags16,group,index.
    Growth owns storage. Missing writable storage raises an authored error after
    membership publication; there is no invented rollback or initial capacity.
    """
    count,capacity=group['count'],group['capacity']
    for v in (count,capacity):
        if type(v) is not int or not 0<=v<=0xffffffff:raise ValueError('Raw uint32 count required')
    flags=body['flags16']
    if type(flags) is not int or not 0<=flags<=0xffff:raise ValueError('Raw metadata flags required')
    if flags&0x8000 and count>=65535:return False
    body['group']=group['token'];body['index']=count
    if count==capacity:grow(group,(capacity*2)&0xffffffff)
    count=group['count']
    if not 0<=count<len(group['slots']):raise ValueError('Writable body slot required')
    group['slots'][count]=body['token']
    group['count']=(count+1)&0xffffffff
    return True


def remove_body_constraints(group, body_token, *, links, poses, clear_link):
    """Reverse-scan two retained constraint arrays and remove matching endpoints.

    links: token -> {first,second,index}; poses also carry group. Clear service
    runs before the link index is reloaded. Structural storage must remain valid.
    """
    for i in range(group['link_count']-1,-1,-1):
        item=links[group['link_slots'][i]]
        if body_token not in (item['first'],item['second']):continue
        clear_link(item)
        index=item['index'];group['link_count']-=1
        count=group['link_count'];slots=group['link_slots']
        slots[index]=slots[count];item['index']=0xffffffff
        if index<count:links[slots[index]]['index']=index
    for i in range(group['pose_count']-1,-1,-1):
        item=poses[group['pose_slots'][i]]
        if body_token not in (item['first'],item['second']):continue
        group['pose_count']-=1;count=group['pose_count'];slots=group['pose_slots']
        slots[i]=slots[count];item['group']=0;item['index']=0xffffffff
        if i<count:
            moved=poses[slots[i]];moved['group']=group['token'];moved['index']=i


def remove_pose_body(group, body, *, bodies, remove_constraints,
                     invalid_index):
    """Remove constraints first, then swap out a valid retained body member.

    invalid_index is the supplied runtime sentinel loaded by the original body
    helper; it is not silently assumed to match the literal pose/link sentinel.
    """
    index=body['index']
    if not (body['group']==group['token'] and 0<=index<group['count']
            and group['slots'][index]==body['token']):
        raise ValueError('Valid retained body membership required')
    if type(invalid_index) is not int or not 0<=invalid_index<=0xffffffff:
        raise ValueError('Raw uint32 sentinel required')
    remove_constraints(group,body['token'])
    index=body['index'];group['count']-=1;count=group['count']
    group['slots'][index]=group['slots'][count]
    if index<count:
        moved=bodies[group['slots'][index]]
        moved['group']=group['token'];moved['index']=index
    body['group']=0;body['index']=invalid_index
