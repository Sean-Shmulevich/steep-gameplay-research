"""Base body registration, typed links, metadata and transform deserialization.

Evidence: docs/reconstruction/LINK_SOLVER.md, Base body identity and metadata loading.
"""
import struct
from .pose_block_reader import select_pose_block, read_pose_block_bytes
from .pose_reference_reader import read_pose_reference


def deserialize_pose_body_metadata(metadata, reader, *, buffers):
    """Load required58-byte metadata block while preserving nonserialized state."""
    if not select_pose_block(reader,0xc05,58,3,True,buffers=buffers):return
    def read(n):return read_pose_block_bytes(reader,n,buffers=buffers)
    for offset in range(4,0x1c,4):metadata[offset:offset+4]=read(4)
    metadata[0x30:0x38]=read(8)
    for offset,size in ((0x38,8),(0x40,8),(0x48,4),(0x4c,4)):
        metadata[offset:offset+size]=read(size)
    low=read(1)[0]&15
    flags=read(1)[0]
    metadata[0x53]=(metadata[0x53]&0xf0)|low
    metadata[0x52]=flags


def deserialize_pose_body_base(body,reader,*,body_token,buffers,metadata,
                               object_tables,fixup_arrays,grow_objects,grow_fixups):
    """Register body before resolving its serialized graph links.

    Does not create metadata, assign a runtime tree key, register with a physics
    provider, decode resource entries or repair links after deferred replay.
    """
    count,capacity=struct.unpack_from('<II',reader,0x30)
    if count==capacity:
        capacity=capacity*2 if capacity else 8
        if capacity>0xffffffff//16:raise ValueError('Object-table allocation exceeds uint32 byte size')
        grow_objects(reader,capacity)
    count=struct.unpack_from('<I',reader,0x30)[0]
    table=object_tables[struct.unpack_from('<Q',reader,0x28)[0]]
    struct.pack_into('<I',reader,0x30,(count+1)&0xffffffff)
    struct.pack_into('<QI',table,count*16,body_token,0x9fb6)
    def select(tag,size,required=False):
        return select_pose_block(reader,tag,size,3,required,buffers=buffers)
    def read(n):return read_pose_block_bytes(reader,n,buffers=buffers)
    def ref(offset,kind):
        if not read_pose_reference(reader,memoryview(body)[offset:offset+8],kind,
                destination_token=body_token+offset,buffers=buffers,
                object_tables=object_tables,fixup_arrays=fixup_arrays,grow_fixups=grow_fixups):
            reader[0x20]=1
    low=read(2) if select(0xc02,2,True) else bytes(2)
    high=read(2) if select(0xc0d,2) else bytes(2)
    body[0x1c:0x20]=low+high
    if select(0xc03,4):ref(0x10,0x9fba)
    else:body[0x10:0x18]=bytes(8)
    deserialize_pose_body_metadata(metadata[struct.unpack_from('<Q',body,0x30)[0]],reader,buffers=buffers)
    if select(0xc06,1,True):
        body[0xaa]=read(1)[0]
        cursor,end=struct.unpack_from('<QQ',reader,0x10)
        body[0xa8:0xaa]=read(2) if cursor+2<=end else bytes(2)
    if select(0xc07,0):ref(0x80,0x9fbb)
    if select(0xc0a,0):ref(0x90,0x9fb9)
    body[0x20:0x28]=read(8) if select(0xc04,8) else bytes(8)
    if select(0xc0b,48):
        for start in range(0x40,0x80,16):
            for offset in range(start,start+12,4):body[offset:offset+4]=read(4)
