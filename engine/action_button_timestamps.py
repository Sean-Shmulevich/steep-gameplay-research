"""Recovered cached-input edge timestamp refresh.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Cached input timestamp edges.
Caller supplies successive cache bytes and both clock sources. No device reads.
"""
from dataclasses import dataclass
import struct

@dataclass(frozen=True)
class ButtonTimestamps:
    current: int
    previous: int
    secondary_current: int
    secondary_previous: int
    keys: tuple
    secondary_keys: tuple
    special: tuple
    secondary_special: tuple


def refresh_button_timestamps(state, *, keys, previous_keys, packet,
                              previous_packet, now, secondary_now):
    """Update stamps only for zero-to-nonzero cache edges; return detached state.

    Ordinary bytes and eight special bytes use nonzero tests, not high-bit tests.
    Special slots 8/9 stamp signed positive/negative values only when previous
    signed value was zero. Direct sign reversal does not refresh either stamp.
    """
    if not isinstance(state,ButtonTimestamps):raise ValueError('ButtonTimestamps required')
    for data,size in ((keys,256),(previous_keys,256),(packet,20),(previous_packet,20)):
        if not isinstance(data,bytes) or len(data)!=size:raise ValueError('exact cache byte lengths required')
    arrays=(state.keys,state.secondary_keys,state.special,state.secondary_special)
    if tuple(map(len,arrays))!=(256,256,10,10):raise ValueError('256 ordinary and 10 special stamps required')
    for value in (state.current,state.previous,state.secondary_current,state.secondary_previous,now,secondary_now,*state.keys,*state.secondary_keys,*state.special,*state.secondary_special):
        if type(value) is not int or not 0<=value<1<<64:raise ValueError('uint64 timestamp required')
    kt,ks,st,ss=map(list,arrays)
    for i in range(256):
        if keys[i] and not previous_keys[i]:kt[i],ks[i]=now,secondary_now
    for i in range(8):
        if packet[12+i] and not previous_packet[12+i]:st[i],ss[i]=now,secondary_now
    current=struct.unpack_from('<i',packet,8)[0]
    previous=struct.unpack_from('<i',previous_packet,8)[0]
    if current and not previous:
        index=8 if current>0 else 9;st[index],ss[index]=now,secondary_now
    return ButtonTimestamps(now,state.current,secondary_now,state.secondary_current,
                            tuple(kt),tuple(ks),tuple(st),tuple(ss))
