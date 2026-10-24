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
