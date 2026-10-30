"""Recovered base constraint object registration and serialized field loading.

Evidence: LINK_SOLVER.md, Base object registration and complete command loading.
"""
import struct
from .pose_block_reader import select_pose_block,read_pose_block_bytes,deserialize_retained_pose_command
from .pose_reference_reader import read_pose_reference


def deserialize_pose_constraint_base(record,reader,*,constraint_token,buffers,
        object_tables,fixup_arrays,grow_objects,grow_fixups,bodies,metadata):
    """Load base state with actual framing/reference readers and explicit growth."""
    count,capacity=struct.unpack_from('<II',reader,0x30)
    if count==capacity:
        new_capacity=capacity*2 if capacity else 8
        if new_capacity>0xffffffff//16:raise ValueError('Object-table allocation exceeds uint32 byte size')
        grow_objects(reader,new_capacity)
    count=struct.unpack_from('<I',reader,0x30)[0]
    table=object_tables[struct.unpack_from('<Q',reader,0x28)[0]]
    struct.pack_into('<I',reader,0x30,(count+1)&0xffffffff)
    struct.pack_into('<QI',table,count*16,constraint_token,0x9fb9)
    def select(tag,size):return select_pose_block(reader,tag,size,3,False,buffers=buffers)
    def read(n):return read_pose_block_bytes(reader,n,buffers=buffers)
    def reference(offset,kind):
        ok=read_pose_reference(reader,memoryview(record)[offset:offset+8],kind,
            destination_token=constraint_token+offset,buffers=buffers,object_tables=object_tables,
            fixup_arrays=fixup_arrays,grow_fixups=grow_fixups)
        if not ok:reader[0x20]=1
    record[0x50:0x58]=read(8) if select(0x301,8) else bytes(8)
    if select(0x2602,9):
        reference(8,0x9fb6)
        if read(1)[0]:reference(0x10,0x9fb6)
        else:struct.pack_into('<Q',record,0x10,0)
    if select(0x2c02,8):
        reference(8,0x9fb6);reference(0x10,0x9fb6)
        def key(token):
            m=struct.unpack_from('<Q',bodies[token],0x30)[0]
            return struct.unpack_from('<I',metadata[m],0x54)[0]
        second=struct.unpack_from('<Q',record,0x10)[0]
        second_key=key(second) if second else 0
        first_key=key(struct.unpack_from('<Q',record,8)[0])
        struct.pack_into('<II',record,0x18,first_key,second_key)
    if select(0x2c03,16):
        for offset in (0x20,0x30,0x28,0x38):reference(offset,0x9fb9)
    if select(0x2609,13):
        reference(0x60,0x9fba)
        record[0x68:0x6c]=read(4)
        record[0x59]=int(read(1)[0]!=0)


def deserialize_pose_command_record(record,reader,*,constraint_token,buffers,
        object_tables,fixup_arrays,grow_objects,grow_fixups,bodies,metadata):
    """Join base object/reference loading to specialized kind4 command loading.

    Does not initialize missing fields, run callback production, replay deferred
    references or register the object into physics provider collections.
    """
    deserialize_retained_pose_command(record,reader,buffers=buffers,
        read_base=lambda r,s:deserialize_pose_constraint_base(r,s,
            constraint_token=constraint_token,buffers=buffers,object_tables=object_tables,
            fixup_arrays=fixup_arrays,grow_objects=grow_objects,grow_fixups=grow_fixups,
            bodies=bodies,metadata=metadata))
