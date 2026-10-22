"""Bounded passive inspection of construction pairs for the inspected build.

Transport must enforce current process identity and timeouts. Matching reads
are not atomic snapshots, lifetime leases or authorization to call native code.
"""
import struct
from .scheduler_observation import _address


def capture_construction_pairs(readv, registry, guards, *, query_identity=None,
                               max_pairs=256):
    _address(registry,0x24)
    if type(max_pairs) is not int or not 0<=max_pairs<=512:
        raise ValueError('pair budget must be 0..512')
    if query_identity is not None and (type(query_identity) is not int or not 0<=query_identity<2**64):
        raise ValueError('optional uint64 query identity required')
    guards=list(guards)
    if not 1<=len(guards)<=30:raise ValueError('provide 1..30 external identity/build guards')
    for address,expected in guards:
        if type(expected) is not bytes or not 1<=len(expected)<=256:
            raise ValueError('bounded byte guards required')
        _address(address,len(expected))

    def read(plan):
        result=list(readv(plan))
        if len(result)!=len(plan) or any(type(b) is not bytes or len(b)!=n for b,(_,n) in zip(result,plan)):
            raise ValueError('incomplete registry read')
        return result
    def check():
        if read([(a,len(b)) for a,b in guards]) != [b for _,b in guards]:
            raise ValueError('registry identity or header changed')
    check()
    header=read([(registry+0x18,12)])[0]
    pointer,packed=struct.unpack('<QI',header);capacity=packed&0x3fff;count=packed>>16
    if count>capacity or count>max_pairs:
        raise ValueError('registry count exceeds capacity or capture budget')
    guards.append((registry+0x18,header))
    plan=[]
    if count:
        _address(pointer,count*16)
        plan=[(pointer+offset,min(256,count*16-offset)) for offset in range(0,count*16,256)]
    first=read(plan) if plan else []
    check()
    second=read(plan) if plan else []
    if second!=first:raise ValueError('registry pair contents changed')
    check()
    rows=list(struct.iter_unpack('<QQ',b''.join(first)))
    labels={}
    def label(value):
        if value==0:return None
        if value not in labels:labels[value]='identity_'+str(len(labels)+1)
        return labels[value]
    public=[dict(key=label(k),target=label(t)) for k,t in rows]
    query=None
    if query_identity is not None:
        match=next((i for i,(k,t) in enumerate(rows) if t==0 or k==query_identity),None)
        query=dict(index=match,target_null=rows[match][1]==0 if match is not None else None,
                   matched_key=rows[match][0]==query_identity if match is not None else None)
    return dict(schema='construction-pairs-observation-v1',count=count,capacity=capacity,
                pairs=public,query=query,null_targets=sum(t==0 for _,t in rows),
                guards_matched=True,contents_rechecked=True,atomic_snapshot=False,
                lifetime_retained=False,safe_native_call_established=False,
                labels_scope='this_capture_only')
