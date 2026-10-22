"""Bounded enumeration of one known processor-chain level.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Ordered processor-chain kernel.
Caller verifies build and root provenance. Does not recurse or call processors.
"""
import struct


def observe_processor_chain(read, processor, expected_table, expected_callback):
    """Two matching semantic receipts; max 8 stages, 104 reads, 728 bytes.

    Handle receipts retain the object pointer and active sign bit, excluding
    unrelated changing bits. This does not guarantee atomicity or lifetime.
    """
    if any(type(x) is not int or not 0<x<1<<64 for x in (processor,expected_table,expected_callback)):
        raise ValueError('nonzero uint64 identities required')
    class Refused(Exception):pass
    def sample():
        receipt=[]
        def get(a,n,mask=None):
            if not 0<a<1<<64 or a+n>1<<64:raise Refused('invalid')
            value=read(a,n)
            if not isinstance(value,bytes) or len(value)!=n:raise Refused('invalid')
            receipt.append((a,value if mask is None else bytes(x&y for x,y in zip(value,mask))))
            return value
        def q(a):return struct.unpack('<Q',get(a,8))[0]
        table=q(processor)
        if table!=expected_table or q(table+0x28)!=expected_callback:raise Refused('unsupported')
        header=get(processor+0xd0,12)
        array=struct.unpack_from('<Q',header)[0];count=struct.unpack_from('<H',header,10)[0]
        if count>8:raise Refused('limit')
        if count and not array:raise Refused('invalid')
        pointers=get(array,8*count) if count else b''
        stages=[]
        for i in range(count):
            child=struct.unpack_from('<Q',pointers,i*8)[0]
            table=q(child)
            if not table:raise Refused('invalid')
            callback=q(table+0x28);handle=q(child+0x10)
            if not handle:raise Refused('invalid')
            obj=q(handle);active=bool(get(handle+15,1,b'\x80')[0]&0x80)
            config=obj if active else 0
            enabled=not config or get(config+0x18,1)!=b'\0'
            stages.append({'processor':child,'table':table,'callback':callback,
                           'configuration':config,'enabled':enabled})
        return stages,tuple(receipt)
    try:
        first,second=sample(),sample()
        return {'status':'observed','stages':first[0]} if first==second else {'status':'unstable'}
    except Refused as exc:return {'status':str(exc)}
    except (OSError,ValueError,struct.error):return {'status':'invalid'}
