"""Passive cached-parent/callback observation using a supplied guarded transport.

No native calls, writes, process acquisition or executable-memory queries.
Evidence: CENTRAL_IMPULSE.md, Passive cached-parent callback reader.
"""
import math
import struct
from .scheduler_observation import _address
from reference.skeleton_parent_transform import cached_parent_callback_gate


def capture_cached_parent(readv, component, entity, skeleton_table, guards, code_ranges=()):
    _address(component,0x2b8);_address(entity,8);_address(skeleton_table,8)
    guards=list(guards)
    if not 1<=len(guards)<=16:raise ValueError('provide 1..16 fresh identity guards')
    for address,value in guards:
        if type(value) is not bytes or not 1<=len(value)<=256:raise ValueError('invalid guard')
        _address(address,len(value))
    ranges=list(code_ranges)
    if len(ranges)>32:raise ValueError('at most 32 supplied code ranges')
    for start,size,label in ranges:
        _address(start,size)
        if type(label) is not str or not 1<=len(label)<=64:raise ValueError('bounded code label required')
    def read(plan):
        result=list(readv(plan))
        if len(result)!=len(plan) or any(type(v) is not bytes or len(v)!=n for v,(_,n) in zip(result,plan)):
            raise ValueError('incomplete cached parent read')
        return result
    def check():
        for i in range(0,len(guards),32):
            group=guards[i:i+32]
            if read([(a,len(v)) for a,v in group])!=[v for a,v in group]:raise ValueError('cached parent identity or state changed')
    def observe(address,size):
        _address(address,size);value=read([(address,size)])[0];guards.append((address,value));return value
    def pose(raw):
        values=struct.unpack('<8f',raw)
        if not all(math.isfinite(v) for v in values):raise ValueError('nonfinite cached parent pose')
        return dict(position=list(values[:4]),rotation=list(values[4:]))
    check()
    if struct.unpack('<Q',observe(component,8))[0]!=skeleton_table:raise ValueError('skeleton table mismatch')
    if struct.unpack('<Q',observe(component+0x10,8))[0]!=entity:raise ValueError('skeleton owner mismatch')
    cached=pose(observe(component+0x130,32))
    primary,current=struct.unpack('<QQ',observe(component+0x250,16))
    raw=observe(component+0x290,40)
    storage,_,tagged,function,holder=struct.unpack('<5Q',raw)
    target=status=0
    if holder:
        target,_,status=struct.unpack('<QII',observe(holder,16))
    elif primary and (storage or tagged&~3):raise ValueError('registered callback has no holder')
    gate=cached_parent_callback_gate(primary_present=bool(primary),storage_word=storage,
        tagged_context=tagged,holder_status=status,holder_target=target)
    primary_pose=pose(observe(primary,32)) if primary else None
    current_pose=pose(observe(current,32)) if current else None
    matches=[label for start,size,label in ranges if function and start<=function<start+size]
    check()
    return dict(schema='cached-parent-observation-v1',cached_parent=cached,
        primary_parent=primary_pose,current_parent=current_pose,
        banks_alias=bool(primary and primary==current),primary_present=bool(primary),current_present=bool(current),
        callback_storage_nonempty=bool(storage or tagged&~3),context_tag=tagged&3,
        forwarded_context_nonzero=bool(tagged&~3),function_present=bool(function),
        holder_present=bool(holder),holder_target_present=bool(target),holder_status_sign_bit=bool(status&0x80000000),
        callback_eligible=gate['invoked'],supplied_code_range_matches=matches,
        guards_matched=True,atomic_snapshot=False,lifetime_pinned=False,
        invocation_observed=False,writer_attribution_established=False,
        executable_memory_verified=False,safe_native_call_established=False)
