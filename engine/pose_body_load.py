"""Recovered body loading entry and known-class resource finalization.

Evidence: LINK_SOLVER.md, Body load entry and resource backlinks.
"""
import struct
from .pose_block_reader import select_pose_block,read_pose_block_bytes


def finalize_pose_body_resources(body,*,entry_arrays,resources):
    """Repair resource owner/index backlinks from native72-byte entry records."""
    count=struct.unpack_from('<H',body,0xc0)[0]
    for i in range(count):
        entries=entry_arrays[struct.unpack_from('<Q',body,0xb8)[0]]
        offset=i*72
        resource=struct.unpack_from('<Q',entries,offset+16)[0]
        if resource:
            index=struct.unpack_from('<I',entries,offset+8)[0]
            owner=struct.unpack_from('<Q',entries,offset)[0]
            struct.pack_into('<Q',resources[resource],0x30,owner)
            struct.pack_into('<I',resources[resource],0x38,index)


def load_pose_body_object(provider,reader,*,buffers,create,deserialize,finalize):
    """Read body kind, create through provider608, deserialize, then finalize.

    create(factory_token,uint16_kind), deserialize(body_token,reader), and
    finalize(body_token) supply dynamic type behavior. Null creation is accepted
    here, unlike the constraint entry's unchecked native result.
    """
    if not select_pose_block(reader,0xc01,4,3,True,buffers=buffers):return 0
    kind=struct.unpack('<H',read_pose_block_bytes(reader,2,buffers=buffers))[0]
    token=create(struct.unpack_from('<Q',provider,0x608)[0],kind)
    if not token:return 0
    deserialize(token,reader)
    finalize(token)
    return token
