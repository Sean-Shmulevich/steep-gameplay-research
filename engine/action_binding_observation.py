"""Bounded manager -> selected bank -> binding map -> action observation.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Manager-to-action observer.
Caller verifies build and supplies exact reads and manager/fallback identities.
No locks, calls into the engine, writes or process access are performed here.
"""
from dataclasses import dataclass
import struct
from .action_map_observation import observe_action_map


@dataclass(frozen=True)
class ActionObservation:
    status: str
    reason: str = ''
    manager: int = 0
    bank: int = 0
    binding: int = 0
    map_root: int = 0
    value_slot: int = 0
    action: int = 0
    table: int = 0
    reset_callback: int = 0
    selected_index: int = 0
    sampled_bits: bytes = b''


def observe_action_binding(read, manager: int, action_id: int, fallback: int) -> ActionObservation:
    """Two matching traversal receipts; max 512 reads / 32768 bytes total.

    Each group allows at most 64 records, 128 visited records total per pass.
    Nonzero writer bits refuse observation; zero is NOT lifetime authorization.
    Reading counters/links twice rejects change but does not exclude ABA races.
    """
    if any(type(v) is not int or not 0 <= v < 1<<64 for v in (manager,fallback)) or not manager:
        raise ValueError('nonzero manager and uint64 fallback required')
    if type(action_id) is not int or not 0<=action_id<1<<32:
        raise ValueError('action ID must be uint32')
    calls=used=0
    class Refused(Exception):
        def __init__(self,status):self.status=status
    def sample():
        nonlocal calls,used
        receipt=[]
        def get(address,n):
            nonlocal calls,used
            if not 0<address<1<<64 or address+n>1<<64:raise Refused('invalid')
            calls+=1;used+=n
            if calls>512 or used>32768:raise Refused('limit')
            data=read(address,n)
            if not isinstance(data,bytes) or len(data)!=n:raise Refused('invalid')
            receipt.append((address,data));return data
        def q(a):return struct.unpack('<Q',get(a,8))[0]
        header=get(manager,0x58)
        if struct.unpack_from('<I',header,12)[0]&0x7ff00000:raise Refused('busy')
        index=struct.unpack_from('<I',header,0x50)[0]
        count=struct.unpack_from('<H',header,0x2a)[0]
        def absent(reason,bank=0,binding=0):
            if not fallback:raise Refused('invalid')
            return ActionObservation('fallback',reason,manager,bank,binding,
                selected_index=index,sampled_bits=get(fallback+0x40,16)),tuple(receipt)
        if index>=count:return absent('selected_index_out_of_range')
        array=struct.unpack_from('<Q',header,0x20)[0]
        if not array:raise Refused('invalid')
        bank=q(array+8*index)
        if not bank:raise Refused('invalid')
        visited=0
        for group in range(3):
            raw=get(bank+0x90+12*group,12)
            records=struct.unpack_from('<Q',raw)[0];n=struct.unpack_from('<H',raw,10)[0]
            if n>64:raise Refused('limit')
            if n and not records:raise Refused('invalid')
            for i in range(n-1,-1,-1):
                visited+=1
                if visited>128:raise Refused('limit')
                binding=q(records+8*i)
                if not binding:raise Refused('invalid')
                map_object=q(binding+0x28)
                if not map_object:raise Refused('invalid')
                root=q(map_object+8)
                result=observe_action_map(get,root,action_id)
                if result.status not in ('found','missing'):raise Refused(result.status)
                if result.status=='found' and result.action:
                    action=result.action;table=q(action)
                    if not table:raise Refused('invalid')
                    callback=q(table+0x10)
                    bits=get(action+0x60,16)
                    return ActionObservation('found','',manager,bank,binding,root,result.value_slot,
                        action,table,callback,index,bits),tuple(receipt)
                config=q(binding+0x20)
                if config and get(config+0x2c,1)!=b'\0':return absent('stop_on_miss',bank,binding)
        return absent('no_action',bank)
    try:
        first,second=sample(),sample()
        return first[0] if first==second else ActionObservation('unstable')
    except Refused as exc:return ActionObservation(exc.status)
    except (OSError,ValueError,struct.error):return ActionObservation('invalid')
