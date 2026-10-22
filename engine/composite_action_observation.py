"""Bounded composite child enumeration; no child callbacks are invoked.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Composite child observation.
Caller verifies build, parent provenance and expected composite table/callback.
Two matching read receipts are not an atomic snapshot or a lifetime guarantee.
"""
from dataclasses import dataclass
import struct

@dataclass(frozen=True)
class CompositeChild:
    action: int
    table: int
    callback: int
    status: int
    payload: bytes
    mode: int | None

@dataclass(frozen=True)
class CompositeObservation:
    status: str
    parent_status: int = 0
    parent_payload: bytes = b''
    children: tuple[CompositeChild, ...] = ()


def observe_composite(read, action, expected_table, expected_callback):
    """At most 16 children, 136 reads and 5600 bytes for both full receipts.

    Enumerates all children, including ones a callback may skip. Never reports
    an actually selected producer from status values observed at another time.
    """
    if any(type(p) is not int or not 0 < p < 1<<64
           for p in (action, expected_table, expected_callback)):
        raise ValueError('nonzero uint64 identities required')
    class Refused(Exception):
        pass
    def sample():
        receipt=[]
        def get(a,n):
            if not 0 < a < 1<<64 or a+n > 1<<64:
                raise Refused('invalid')
            data=read(a,n)
            if not isinstance(data,bytes) or len(data)!=n:
                raise Refused('invalid')
            receipt.append((a,data))
            return data
        def q(a): return struct.unpack('<Q',get(a,8))[0]
        header=get(action,0xc4)
        table=struct.unpack_from('<Q',header)[0]
        if table!=expected_table: raise Refused('unsupported')
        if q(table+16)!=expected_callback: raise Refused('unsupported')
        config,array=struct.unpack_from('<QQ',header,0xb0)
        count=struct.unpack_from('<H',header,0xc2)[0]
        if not config: raise Refused('unavailable')
        if count>16: raise Refused('limit')
        if count and not array: raise Refused('invalid')
        pointers=get(array,8*count) if count else b''
        records=q(config+0x28) if count>1 else 0
        if count>1 and not records: raise Refused('invalid')
        children=[]
        for i in range(count):
            child=struct.unpack_from('<Q',pointers,8*i)[0]
            raw=get(child,0x84)
            child_table=struct.unpack_from('<Q',raw)[0]
            if not child_table: raise Refused('invalid')
            callback=q(child_table+16)
            mode=None
            if i<count-1:
                record=q(records+8*i)
                if not record: raise Refused('invalid')
                mode=struct.unpack('<I',get(record+16,4))[0]
            children.append(CompositeChild(child,child_table,callback,raw[0x30],raw[0x50:0x84],mode))
        result=CompositeObservation('observed',header[0x30],header[0x50:0x84],tuple(children))
        return result,tuple(receipt)
    try:
        first,second=sample(),sample()
        return first[0] if first==second else CompositeObservation('unstable')
    except Refused as exc: return CompositeObservation(str(exc))
    except (OSError,ValueError,struct.error): return CompositeObservation('invalid')
