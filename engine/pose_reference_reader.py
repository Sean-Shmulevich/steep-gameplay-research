"""Recovered typed pointer reads and deferred-reference enqueue.

Evidence: LINK_SOLVER.md, Typed references and deferred writes.
"""
import struct
from .pose_block_reader import read_pose_block_bytes


def read_pose_reference(reader,destination,expected_type,*,destination_token,
        buffers,object_tables,fixup_arrays,grow_fixups,reference_counted=False,
        retain=None):
    """Resolve or enqueue a typed reference, returning native success semantics.

    destination is a writable8-byte view; destination_token identifies that exact
    slot for deferred replay. grow_fixups(reader,new_capacity) updates descriptor38
    and preserves records. retain(token) supplies atomic uint32 increment at+8 for
    the counted variant. It is called after publishing the resolved pointer.
    Reader errors are set by callers, not this routine. No rollback is performed.
    """
    expected_type&=0xffffffff
    word=struct.unpack('<I',read_pose_block_bytes(reader,4,buffers=buffers))[0]
    if word&0xffff0000!=0x73cb0000 or word&0xffff!=expected_type:return False
    index=struct.unpack('<I',read_pose_block_bytes(reader,4,buffers=buffers))[0]
    if not reference_counted and index==0xffffeeee:
        struct.pack_into('<Q',destination,0,0);return True
    count=struct.unpack_from('<I',reader,0x30)[0]
    if index<count:
        table=object_tables[struct.unpack_from('<Q',reader,0x28)[0]]
        offset=index*16
        if struct.unpack_from('<I',table,offset+8)[0]!=expected_type:return False
        token=struct.unpack_from('<Q',table,offset)[0]
        struct.pack_into('<Q',destination,0,token)
        if reference_counted:
            if retain is None:raise ValueError('Counted reference requires retain service')
            retain(token)
        return True
    count,capacity=struct.unpack_from('<II',reader,0x40)
    if count==capacity:
        new_capacity=capacity*2 if capacity else 8
        if new_capacity>0xffffffff//24:
            raise ValueError('Fixup allocation exceeds uint32 byte size')
        grow_fixups(reader,new_capacity)
    count=struct.unpack_from('<I',reader,0x40)[0]
    rows=fixup_arrays[struct.unpack_from('<Q',reader,0x38)[0]]
    struct.pack_into('<I',reader,0x40,(count+1)&0xffffffff)
    offset=count*24
    struct.pack_into('<I',rows,offset+8,index)
    struct.pack_into('<Q',rows,offset,destination_token)
    struct.pack_into('<I',rows,offset+12,expected_type)
    rows[offset+16]=int(reference_counted)
    return True
