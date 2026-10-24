"""Recovered pose attachment service ordering.

Evidence: CENTRAL_IMPULSE.md, Pose body-group attachment.
Services own native effects, group lifetime and synchronization.
"""


def attach_pose_record(context, record, first_body, second_body, request_byte,
                       *, prepare_group, merge_groups, append_record):
    """Capture group identities for decisions, reload first group for append.

    Body dictionaries expose 'group' as an opaque uint64 identity. Supplied
    services may update those dictionaries. Normal-return serial execution only;
    failures propagate without an invented rollback or cleanup guarantee.
    """
    if type(request_byte) is not int or not 0<=request_byte<=255:
        raise ValueError('Raw uint8 request required')
    if second_body is not None:
        first_group=first_body['group'];second_group=second_body['group']
        if request_byte!=0:
            prepare_group(context,first_group)
            prepare_group(context,second_group)
        if first_group!=second_group:
            merge_groups(context,first_body,second_body)
    return append_record(first_body['group'],record)


def append_pose_record(group, record, *, grow):
    """Append to a supplied valid group array, with native publication order.

    group: token, count, capacity, slots. record: token plus mutable group/index.
    grow(group, requested_capacity) must supply writable slots on normal return.
    No allocator failure recovery, duplicate prevention or lifetime pin is added.
    """
    count=group['count']
    if type(count) is not int or not 0<=count<=0xffffffff:
        raise ValueError('Unsigned group count required')
    if count>=65535:return False
    record['group']=group['token'];record['index']=count
    capacity=group['capacity']
    if count==capacity:
        grow(group,8 if capacity==0 else (capacity*2)&0xffffffff)
    index=group['count']
    if not 0<=index<len(group['slots']):
        raise ValueError('Missing writable storage after publication; native failure behavior unresolved')
    group['slots'][index]=record['token']
    group['count']=(index+1)&0xffffffff
    return True
