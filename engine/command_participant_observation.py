"""Bounded structural observation of the inspected engine command participant list.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, command executor and preparation.
Caller qualifies process/build and supplies singleton and image/code ranges.
This observes method pointers; it does not prove invocation or object lifetime.
"""
import struct


def observe_command_participants(read, *, singleton_address, image_range, code_range):
    for lo, hi in (image_range, code_range):
        if type(lo) is not int or type(hi) is not int or not 0 < lo < hi <= 2**64:
            raise ValueError('ordered uint64 ranges required')
    if not image_range[0] <= code_range[0] < code_range[1] <= image_range[1]:
        raise ValueError('code range must belong to image')
    if type(singleton_address) is not int or not image_range[0] <= singleton_address < image_range[1]-7:
        raise ValueError('singleton must belong to image')
    reads=total=0
    class Refused(Exception):pass
    def get(a,n):
        nonlocal reads,total
        if not 0<a<2**64 or a+n>2**64:raise Refused('invalid_address')
        if reads>=134 or total+n>2100:raise Refused('limit')
        reads+=1;total+=n
        value=read(a,n)
        if not isinstance(value,bytes) or len(value)!=n:raise Refused('short_read')
        return value
    def q(a):return struct.unpack('<Q',get(a,8))[0]
    def sample():
        manager=q(singleton_address)
        if not manager:raise Refused('manager_unavailable')
        header=get(manager+0xb0,12)
        array=struct.unpack_from('<Q',header)[0]
        count=struct.unpack_from('<H',header,10)[0]
        if count>32:raise Refused('limit')
        pointers=struct.unpack('<'+'Q'*count,get(array,8*count)) if count else ()
        entries=[]
        for pointer in pointers:
            table=q(pointer)
            if not image_range[0]<=table<=image_range[1]-16:raise Refused('table_outside_image')
            execute,prepare=struct.unpack('<QQ',get(table,16))
            if not all(code_range[0]<=x<code_range[1] for x in (execute,prepare)):
                raise Refused('method_outside_code')
            entries.append(dict(object=pointer,table=table,execute=execute,prepare=prepare))
        return dict(manager=manager,array=array,count=count,header_bits=header.hex(),entries=entries)
    try:
        a,b=sample(),sample()
        result=dict(status='observed',registry=a) if a==b else dict(status='unstable')
    except Refused as exc:result=dict(status=str(exc))
    except (OSError,ValueError,struct.error):result=dict(status='invalid')
    return dict(result,reads=reads,bytes=total,atomic_snapshot=False,execution_proved=False)
