"""Bounded vector/directional source and processor configuration observation.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Source configuration observation.
Caller verifies build, child provenance and concrete table/callback identities.
No execution, device labels, atomicity or input freshness is inferred.
"""
import struct
from .vector_action_source import priority_blocks, cached_value, select_vector_source


def observe_action_source(read, action, table, callback, family, priority_slot=None):
    """Two matching receipts, at most 64 reads / 4096 bytes total.

    Reads cached bytes even if a gate would suppress their consumption.
    derived_source_bits is a detached calculation from the observed gates.
    """
    if family not in ('vector','directional'):
        raise ValueError('explicit known family required')
    ids=(action,table,callback)+((priority_slot,) if family=='vector' else ())
    if any(type(x) is not int or not 0<x<1<<64 for x in ids):
        raise ValueError('nonzero uint64 identities required')
    calls=used=0
    class Refused(Exception):pass
    def sample():
        receipt=[]
        def get(a,n,mask=None):
            nonlocal calls,used
            if not 0<a<1<<64 or a+n>1<<64:raise Refused('invalid')
            calls+=1;used+=n
            if calls>64 or used>4096:raise Refused('limit')
            data=read(a,n)
            if not isinstance(data,bytes) or len(data)!=n:raise Refused('invalid')
            observed=data if mask is None else bytes(x&y for x,y in zip(data,mask))
            receipt.append((a,observed));return data
        def q(a):return struct.unpack('<Q',get(a,8))[0]
        h=get(action,0xc0)
        if struct.unpack_from('<Q',h)[0]!=table or q(table+16)!=callback:
            raise Refused('unsupported')
        owner=struct.unpack_from('<Q',h,16)[0]
        processor,config=struct.unpack_from('<QQ',h,0xb0)
        if not config or not processor or not owner:raise Refused('unavailable')
        cfg=get(config,0x38 if family=='vector' else 0x50)
        ph=get(processor,0x18);pt=struct.unpack_from('<Q',ph)[0]
        handle=struct.unpack_from('<Q',ph,16)[0]
        if not pt or not handle:raise Refused('invalid')
        process=q(pt+0x28)
        handle_object=q(handle)
        # Only the sign bit participates in the caller's handle resolution.
        active=bool(get(handle+15,1,mask=b'\x80')[0]&0x80)
        resolved=handle_object if active else 0
        enabled=not resolved or get(resolved+0x18,1)!=b'\0'
        own=get(owner,12);cache,index=struct.unpack('<QI',own)
        d={'family':family,'owner':owner,'owner_index':index,'cache':cache,
           'configuration':config,'processor':processor,'processor_table':pt,
           'processor_callback':process,'processor_configuration':resolved,
           'processing_enabled':enabled}
        if family=='directional':
            d['query_ids']=list(struct.unpack_from('<8I',cfg,0x30))
        else:
            kind,lane=struct.unpack_from('<II',cfg,0x30)
            if kind>3:raise Refused('unsupported')
            channel=kind if kind<2 else (10 if kind==2 else 12)
            priority=q(priority_slot)
            if not priority or not cache:raise Refused('invalid')
            high=priority+(0xf050 if kind<2 else 0x850)+0xe8*(index+channel*8)
            slots=list(reversed(struct.unpack('<7Q',get(high-48,56))))
            blocked=priority_blocks(owner,slots)
            mh=get(cache+0x248,12);array=struct.unpack_from('<Q',mh)[0]
            count=struct.unpack_from('<H',mh,10)[0]
            if count and not array:raise Refused('invalid')
            top=q(array+8*(count-1)) if count else 0
            offset=0x1f0+16*channel if kind<2 else 0x168+4*channel
            raw=get(cache+offset,16 if kind<2 else 4)
            masked=cached_value(raw,[top] if count else [])
            derived=select_vector_source(kind,lane,lambda *a:blocked,lambda i:masked,lambda i:masked)
            d.update(source_kind=kind,lane_mode=lane,channel=channel,
                     ownership_slots=slots,ownership_blocked=blocked,mask_count=count,
                     mask_top=top,mask_blocked=bool(top),cached_bits=raw.hex(),
                     derived_source_bits=derived.hex())
        return d,tuple(receipt)
    try:
        first,second=sample(),sample()
        return {'status':'observed','details':first[0]} if first==second else {'status':'unstable'}
    except Refused as exc:return {'status':str(exc)}
    except (OSError,ValueError,struct.error):return {'status':'invalid'}
