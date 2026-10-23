"""Bounded passive history-action observations, not an atomic snapshot.

Evidence: INPUT_TO_ACTION_ROUTE.md, Passive history-action capture contract.
Caller verifies build and fresh action provenance. Addresses are session-private.
No native calls, polling, installation or writes are performed here.
"""
import struct


def observe_history_action(read, action, *, expected_table, expected_callback,
                           receiver_slot, fallback_clock_slot):
    """Return two observations, keeping dynamic samples separate from identity.

    Maximum 32 reads and 1,024 requested bytes. Matching identities do not prove
    lifetime, atomicity, execution or freshness. Values may change between reads.
    """
    for value in (action,expected_table,expected_callback,receiver_slot,fallback_clock_slot):
        if type(value) is not int or not 0 < value < 1<<64:
            raise ValueError('nonzero uint64 identities required')
    calls=used=0
    class Refused(Exception):pass
    def get(address,size):
        nonlocal calls,used
        if not 0<address<1<<64 or address+size>1<<64:raise Refused('invalid')
        if calls+1>32 or used+size>1024:raise Refused('limit')
        calls+=1;used+=size
        data=read(address,size)
        if not isinstance(data,bytes) or len(data)!=size:raise Refused('invalid')
        return data
    def q(address):return struct.unpack('<Q',get(address,8))[0]
    def sample():
        raw=get(action,0xd0)
        table=struct.unpack_from('<Q',raw)[0]
        if table!=expected_table or q(table+0x10)!=expected_callback:
            raise Refused('unsupported')
        owner=struct.unpack_from('<Q',raw,0x10)[0]
        config=struct.unpack_from('<Q',raw,0xb0)[0]
        if not owner or not config:raise Refused('unavailable')
        settings=get(config+0x28,20)
        channel,kind,mode=struct.unpack_from('<3I',settings)
        if channel>1:raise Refused('unsupported')
        owner_header=get(owner,12)
        reference=get(owner+0x790,16)
        history=owner+0x10+channel*0x3c0
        threshold_header=get(history+0x3a0,12)
        threshold_pointer=struct.unpack_from('<Q',threshold_header)[0]
        threshold_count=struct.unpack_from('<H',threshold_header,10)[0]
        if not threshold_pointer or not threshold_count:raise Refused('unavailable')
        threshold_bits=get(threshold_pointer,4).hex()
        times=get(history,24)
        b=get(history+0x1a0,16);c=get(history+0x240,16)
        magnitude=get(history+0x2e0,4)
        receiver=q(receiver_slot)
        selected=q(receiver+0x188) if receiver else 0
        clock=selected+0x1048 if selected else q(fallback_clock_slot)
        if not clock:raise Refused('unavailable')
        tick=q(clock+8)
        identity=dict(action=action,table=table,callback=expected_callback,
            owner=owner,configuration=config,channel=channel,history=history,
            owner_header_bits=owner_header.hex(),settings_bits=settings.hex(),
            reference_bits=reference.hex(),threshold_header_bits=threshold_header.hex(),
            threshold_bits=threshold_bits,receiver=receiver,selected=selected,clock_record=clock)
        values=dict(action_active_byte=raw[0x30],cached_predicate_byte=raw[0xb8],
            action_magnitude_bits=raw[0x60:0x64].hex(),
            start_time=struct.unpack_from('<Q',raw,0xc0)[0],repeat_time=struct.unpack_from('<Q',raw,0xc8)[0],
            history_times=list(struct.unpack('<3Q',times)),history_b_bits=b.hex(),
            history_c_bits=c.hex(),history_magnitude_bits=magnitude.hex(),clock_ticks=tick)
        return dict(identity=identity,values=values)
    try:
        first,second=sample(),sample()
        status='observed' if first['identity']==second['identity'] else 'unstable'
        result=dict(status=status,observations=[first,second],
                    dynamic_values_equal=first['values']==second['values'])
    except Refused as exc:result=dict(status=str(exc))
    except (OSError,ValueError,struct.error):result=dict(status='invalid')
    result.update(reads=calls,bytes=used,atomic=False,execution_proven=False,freshness_proven=False)
    return result
