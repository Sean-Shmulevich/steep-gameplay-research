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


def replay_pose_references(reader,*,object_tables,fixup_arrays,destinations,
        allocate_scratch,release_scratch,grow_fixups,retain):
    """Resolve pending rows, zero failures and retain only failures for retry.

    destinations maps exact slot tokens to writable8-byte views. Scratch allocation
    receives byte count and returns writable storage; release receives that storage.
    Valid serial capacity is required. Native scratch reallocation under allocator-
    driven queue mutation is outside this adapter's contract.
    """
    initial_count=struct.unpack_from('<I',reader,0x40)[0]
    scratch=allocate_scratch(initial_count*24) if initial_count else bytearray()
    count=struct.unpack_from('<I',reader,0x40)[0]
    object_count=struct.unpack_from('<I',reader,0x30)[0]
    rows=fixup_arrays[struct.unpack_from('<Q',reader,0x38)[0]] if count else b''
    pending=0
    for i in range(count):
        offset=i*24
        index=struct.unpack_from('<I',rows,offset+8)[0]
        valid=index<object_count
        table=None
        if valid:
            table=object_tables[struct.unpack_from('<Q',reader,0x28)[0]]
            valid=struct.unpack_from('<I',rows,offset+12)[0]==struct.unpack_from('<I',table,index*16+8)[0]
        slot=struct.unpack_from('<Q',rows,offset)[0]
        if valid:
            pointer=struct.unpack_from('<Q',table,index*16)[0]
            struct.pack_into('<Q',destinations[slot],0,pointer)
            if rows[offset+16]:
                slot=struct.unpack_from('<Q',rows,offset)[0]
                retain(struct.unpack_from('<Q',destinations[slot],0)[0])
        else:
            struct.pack_into('<Q',destinations[slot],0,0)
            if (pending+1)*24>len(scratch):
                raise ValueError('Fixup span grew beyond allocated scratch capacity')
            scratch[pending*24:(pending+1)*24]=rows[offset:offset+24]
            pending+=1
    struct.pack_into('<I',reader,0x40,0)
    capacity=struct.unpack_from('<I',reader,0x44)[0]
    if pending>capacity:
        new_capacity=capacity or pending
        while new_capacity<pending:new_capacity*=2
        if new_capacity>0xffffffff//24:raise ValueError('Fixup allocation exceeds uint32 byte size')
        grow_fixups(reader,new_capacity)
    struct.pack_into('<I',reader,0x40,pending)
    if pending:
        target=fixup_arrays[struct.unpack_from('<Q',reader,0x38)[0]]
        target[:pending*24]=scratch[:pending*24]
    if initial_count:release_scratch(scratch)
    return pending==0
