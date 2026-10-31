"""Body resource-entry reader with recovered legacy flag fallback.

Evidence: docs/reconstruction/LINK_SOLVER.md, Serialized body resource entries.
"""
import struct
from .pose_block_reader import select_pose_block, read_pose_block_bytes
from .pose_reference_reader import read_pose_reference


def deserialize_pose_resource_entry(entry, reader, body, *, entry_token, buffers,
        metadata, object_tables, fixup_arrays, grow_fixups, set_transform):
    """Read one required0e03 entry; transform ownership remains a supplied service.

    set_transform(entry, packed_xyz48) receives four XYZ triples after flags and
    all other fields have been written. It owns the transform pointer at entry18.
    No padding lanes are invented from native uninitialized stack bytes.
    """
    if not select_pose_block(reader,0xe03,95,3,True,buffers=buffers):return
    def read(n):return read_pose_block_bytes(reader,n,buffers=buffers)
    if not read_pose_reference(reader,memoryview(entry)[16:24],0x9fb7,
            destination_token=entry_token+16,buffers=buffers,object_tables=object_tables,
            fixup_arrays=fixup_arrays,grow_fixups=grow_fixups):
        reader[0x20]=1
    frame=read(48)
    for offset,size in ((0x20,8),(0x28,8),(0x30,8),(0x38,4),(0x3c,4),(0x40,4)):
        entry[offset:offset+size]=read(size)
    first,second,third=read(3)
    def optional(default):
        cursor,end=struct.unpack_from('<QQ',reader,0x10)
        return read(1)[0] if cursor+1<=end else default
    fourth=optional(0)
    cursor,end=struct.unpack_from('<QQ',reader,0x10)
    if (cursor&0xffffffff)==(end&0xffffffff):
        meta=metadata[struct.unpack_from('<Q',body,0x30)[0]]
        priority=struct.unpack_from('<H',meta,0x50)[0]&0x8000
        fifth=int(not priority or bool(meta[0x52]&8) or first!=0)
    else:
        fifth=optional(0)
    sixth=optional(1)
    entry[0x44]=(entry[0x44]&0xc0)|sum((v&1)<<bit for bit,v in
        enumerate((sixth,first,fifth,second,third,fourth)))
    set_transform(entry,frame)
