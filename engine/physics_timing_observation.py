"""Bounded reader for the inspected physics timing state and history ring.

Evidence: SCHEDULER_SMOOTHING_AUDIT.md and SCHEDULER_LIFETIME_AUDIT.md.
Caller establishes process/build identity and fresh timing-owner provenance.
No game calls or writes. Equal sequential reads do not establish atomicity.
"""
import math
import struct


def observe_physics_timing(read, owner, physics_manager, policy_address):
    """Two equal samples, at most 12 reads/658 bytes; history capacity <=64.

    Runtime pointers are private provenance and must be stripped for publication.
    The world interval is observed now, not proven to be this batch's input.
    Returned retained time is the current field, not inferred pre-update time.
    """
    for address in (owner, physics_manager, policy_address):
        if type(address) is not int or not 0 < address < 1 << 64:
            raise ValueError('nonzero uint64 addresses required')
    reads=total=0
    class Refused(Exception):pass
    def get(address,size):
        nonlocal reads,total
        if not 0 < address < 1<<64 or address+size>1<<64:raise Refused('invalid_address')
        if reads>=12 or total+size>658:raise Refused('limit')
        reads+=1;total+=size
        data=read(address,size)
        if not isinstance(data,bytes) or len(data)!=size:raise Refused('short_read')
        return data
    def q(address):return struct.unpack('<Q',get(address,8))[0]
    def sample():
        if q(owner)!=physics_manager:raise Refused('owner_changed')
        raw=get(owner+0x1368,52)
        retained,consumed,inverse,frequency=struct.unpack_from('<4f',raw)
        history=struct.unpack_from('<Q',raw,16)[0]
        count,write,oldest,capacity,steps=struct.unpack_from('<5I',raw,24)
        elapsed=struct.unpack_from('<f',raw,44)[0]
        policy=get(policy_address,1)[0]
        if capacity>64:raise Refused('limit')
        if count>capacity:raise Refused('invalid_ring')
        if capacity:
            if not history or write>=capacity or oldest>=capacity or write!=(oldest+count)%capacity:
                raise Refused('invalid_ring')
        elif count or write or oldest:raise Refused('invalid_ring')
        # Only read allocated storage; unused lanes may contain arbitrary bits.
        payload=get(history,capacity*4) if capacity else b''
        bits=list(struct.unpack('<'+'I'*capacity,payload)) if capacity else []
        chronological=[bits[(oldest+i)%capacity] for i in range(count)]
        values=[struct.unpack('<f',struct.pack('<I',x))[0] for x in chronological]
        if not all(math.isfinite(x) and x>=0 for x in (retained,consumed,inverse,elapsed,*values)) or not math.isfinite(frequency) or frequency<=0:
            raise Refused('unsupported_values')
        world=q(physics_manager+8)
        interval=get(world+0x1060,4) if world else bytes(4)
        current=struct.unpack('<f',interval)[0]
        if not math.isfinite(current) or current<0:raise Refused('unsupported_values')
        return dict(owner=owner,physics_manager=physics_manager,world=world,
            history_pointer=history,retained=retained,consumed=consumed,
            inverse_consumed=inverse,frequency=frequency,step_count=steps,elapsed=elapsed,
            smoothing_enabled=bool(raw[48]),policy=policy,history_count=count,
            history_write=write,history_oldest=oldest,history_capacity=capacity,
            history_bits=bits,chronological_history_bits=chronological,
            world_interval_observed=current,semantic_header_hex=raw[:49].hex(),
            world_interval_hex=interval.hex())
    try:
        first,second=sample(),sample()
        result=dict(status='observed',timing=first) if first==second else dict(status='unstable')
    except Refused as exc:result=dict(status=str(exc))
    except (OSError,ValueError,struct.error):result=dict(status='invalid')
    return dict(result,reads=reads,bytes=total,atomic_snapshot=False,
                producer_input_proved=False)
