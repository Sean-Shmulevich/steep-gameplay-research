"""Recovered tagged-block selector and bounded payload-read adapter.

Evidence: LINK_SOLVER.md, Tagged block framing and cursor rules.
"""
import struct


def _storage(reader,buffers):
    base=struct.unpack_from('<Q',reader,0)[0]
    size=struct.unpack_from('<I',reader,8)[0]
    data=buffers[base]
    if size>len(data) or base+size>0xffffffffffffffff:
        raise ValueError('Complete nonwrapping reader storage required')
    return base,size,data


def select_pose_block(reader,tag,size,scan_limit,required,*,buffers):
    """Select an ECD7 block, leaving cursors unchanged on failure.

    Reader offsets: buffer0,length8,payload cursor10,next block18,error byte20.
    Header words: ECD70000|tag and total bytes including the8-byte header.
    Arguments mirror native uint32 tag/size/scan_limit and low-byte required.
    """
    base,length,data=_storage(reader,buffers)
    cursor=struct.unpack_from('<Q',reader,0x18)[0]-base
    if not 0<=cursor<=length:
        raise ValueError('Next-block cursor outside retained buffer')
    tag&=0xffffffff;size&=0xffffffff;scan_limit&=0xffffffff
    for _ in range(scan_limit):
        if cursor+8>length:break
        word,total=struct.unpack_from('<II',data,cursor)
        if word&0xffff0000!=0xecd70000 or total<8 or cursor+total>length:
            reader[0x20]=1;return False
        if word&0xffff==tag:
            if total<size+8:
                reader[0x20]=1;return False
            struct.pack_into('<QQ',reader,0x10,base+cursor+8,base+cursor+total)
            return True
        cursor+=total
    if int(required)&255:reader[0x20]=1
    return False


def read_pose_block_bytes(reader,size,*,buffers):
    """Authored bounded adapter for inline native payload loads/cursor advances."""
    base,length,data=_storage(reader,buffers)
    cursor,end=struct.unpack_from('<QQ',reader,0x10)
    offset=cursor-base
    if size<0 or offset<0 or cursor+size>end or end>base+length:
        raise ValueError('Payload read outside selected block')
    result=bytes(data[offset:offset+size])
    struct.pack_into('<Q',reader,0x10,cursor+size)
    return result


def deserialize_retained_pose_command(record,reader,*,buffers,read_base):
    """Join actual block framing/cursor reads to the kind4 command consumer.

    Base object/reference loading remains explicit. No asset envelope, reference
    fixups or callback identity are inferred from these command blocks.
    """
    from .pose_command_decode import deserialize_pose_command_constraint
    deserialize_pose_command_constraint(record,reader,read_base=read_base,
        select_block=lambda r,t,s,n,f:select_pose_block(r,t,s,n,f,buffers=buffers),
        read_bytes=lambda r,n:read_pose_block_bytes(r,n,buffers=buffers))
