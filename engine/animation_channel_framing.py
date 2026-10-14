"""Serialized framing only; value decoding support is a separate contract.

Widths/time layouts are from Studio animation format sections 6.2-6.3, plus
encoding-zero's inspected serializer. No native value semantics are inferred.
"""
import struct

# Observed Studio families plus the independently inspected float4 family.
ELEMENT_BYTES={0:16,3:4,4:6,5:8,7:2,8:12,9:12,11:6,12:4,13:1,
               14:2,16:1,18:4,19:4,22:8}


def frame_serialized_channel(data,offset=0):
    data=memoryview(data)
    if type(offset) is not int or offset<0 or offset+9>len(data):
        raise ValueError('truncated serialized channel header')
    tag=data[offset];family,time_format=divmod(tag,3)
    if family not in ELEMENT_BYTES:raise ValueError('unsupported serialized channel framing')
    allocation,count=struct.unpack_from('<II',data,offset+1)
    if count==0:raise ValueError('zero-key serialized channel')
    cursor=offset+9;mode=None
    if time_format==2:
        if cursor>=len(data):raise ValueError('missing mask mode')
        mode=data[cursor];cursor+=1;size=mode&63
        if not size or cursor+size>len(data):raise ValueError('truncated time mask')
        mask=int.from_bytes(data[cursor:cursor+size],'little')
        if not mask&1 or mask.bit_count()!=count:raise ValueError('mask key count mismatch')
        cursor+=size
    else:
        width=time_format+1;size=(count-1)*width
        if size>len(data)-cursor:raise ValueError('truncated key times')
        previous=0
        for i in range(count-1):
            tick=data[cursor+i] if width==1 else struct.unpack_from('<H',data,cursor+2*i)[0]
            if tick<previous:raise ValueError('unsorted key times')
            previous=tick
        cursor+=size
    sample_bytes=ELEMENT_BYTES[family];end=cursor+count*sample_bytes
    if end>len(data):raise ValueError('truncated serialized samples')
    return {'encoding':tag,'count':count,'opaque_allocation':allocation,
            'sample_bytes':sample_bytes,'sample_offset':cursor,'time_format':time_format,
            'mode':mode,'consumed':end-offset}
