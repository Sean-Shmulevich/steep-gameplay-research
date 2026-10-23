"""Bounded read-only inspection of registered markup listener copies.

See CENTRAL_IMPULSE.md, Bounded registered-listener observation. Transport owns
process identity/timeouts. Guards do not pin memory or authorize native calls.
"""
import struct
from .action_map_observation import observe_action_map
from .scheduler_observation import _address


def observe_markup_listeners(read, dispatcher, markup_id, guards, *, max_listeners=16):
    _address(dispatcher,0x68)
    if type(markup_id) is not int or not 0<=markup_id<4096:
        raise ValueError('markup ID must be 0..4095')
    if type(max_listeners) is not int or not 0<=max_listeners<=128:
        raise ValueError('listener budget must be 0..128')
    guards=list(guards)
    if not 1<=len(guards)<=16:raise ValueError('provide 1..16 identity/ownership guards')
    for at,expected in guards:
        if type(expected) is not bytes or not 1<=len(expected)<=256:
            raise ValueError('bounded byte guards required')
        _address(at,len(expected))
    calls=total=0
    def get(at,n):
        nonlocal calls,total
        _address(at,n);calls+=1;total+=n
        if calls>320 or total>49152:raise ValueError('listener observation budget exceeded')
        data=read(at,n)
        if type(data) is not bytes or len(data)!=n:raise ValueError('incomplete listener read')
        return data
    def check_guards():
        for at,expected in guards:
            if get(at,len(expected))!=expected:raise ValueError('identity/ownership guard changed')
    check_guards()
    header=get(dispatcher+0x50,24)
    records=struct.unpack_from('<Q',header)[0]
    count=struct.unpack_from('<H',header,10)[0]
    root=struct.unpack_from('<Q',header,16)[0]
    if not markup_id<count<=4096:raise ValueError('markup index/count outside inspected bounds')
    _address(records,count*20)
    record=get(records+markup_id*20,20)
    first=observe_action_map(get,root,markup_id)
    entries=[];vector_header=None;payload=None
    if first.status=='found' and first.action:
        _address(first.action,20)
        vector_header=get(first.action+8,12)
        array,n=struct.unpack_from('<Q',vector_header)[0],struct.unpack_from('<H',vector_header,10)[0]
        if n>max_listeners:raise ValueError('listener count exceeds budget')
        if n:
            _address(array,n*40);payload=get(array,n*40)
            for index in range(n):
                table,function,adjustment,tagged,thunk=struct.unpack_from('<5Q',payload,index*40)
                entries.append(dict(index=index,entry_address=array+index*40,table=table,
                    function=function,adjustment=adjustment,receiver=tagged&~3,
                    receiver_tags=tagged&3,thunk=thunk,
                    callable_in_dispatch=bool((tagged&~3) or function)))
        else:payload=b''
    second=observe_action_map(get,root,markup_id)
    if second!=first:raise ValueError('listener map changed')
    if vector_header is not None:
        if get(first.action+8,12)!=vector_header:raise ValueError('listener vector changed')
        if payload and get(array,len(payload))!=payload:raise ValueError('listener descriptors changed')
    if get(records+markup_id*20,20)!=record or get(dispatcher+0x50,24)!=header:
        raise ValueError('markup header/record changed')
    check_guards()
    status='present_null' if first.status=='found' and not first.action else first.status
    return dict(status=status,markup_id=markup_id,record_count=count,
        link_count=struct.unpack_from('<i',record,16)[0],cached_value=record[14],
        force_flag=record[13],pending_index=struct.unpack_from('<i',record,8)[0],
        value_slot=first.value_slot,listener_vector=first.action,entries=entries,
        reads=calls,bytes_read=total,atomic_snapshot=False,lifetime_proved=False,
        callback_execution_proved=False)
