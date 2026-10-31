"""Body resource-array replacement and entry dispatch.

Evidence: docs/reconstruction/LINK_SOLVER.md, Resource-array loading lifecycle.
"""
import struct
from .pose_block_reader import select_pose_block,read_pose_block_bytes
from .pose_transform_storage import initialize_pose_transform

IDENTITY_XYZ=struct.pack('<12f',1,0,0,0,1,0,0,0,1,0,0,0)


def deserialize_pose_body_resource_array(body,reader,*,body_token,buffers,
        entry_arrays,identity_token,read_base,reset_resource,grow_entries,read_entry):
    """Read base, optional transform and resource array with supplied lifecycle calls.

    reset_resource(body,index,identity_xyz,0) supplies virtualD0. grow_entries(body,
    capacity) updates b8/c2. read_entry(entry,reader,body,entry_token) supplies actual
    entry decoding. Defaults use recovered transform construction, not fabricated
    resources. Native nonterminating uint16 growth becomes an authored ValueError.
    """
    read_base(body,reader)
    def select(tag,size,scans=3):
        return select_pose_block(reader,tag,size,scans,False,buffers=buffers)
    def read(n):return read_pose_block_bytes(reader,n,buffers=buffers)
    if select(0xe01,48):
        for start in range(0x40,0x80,16):
            for offset in range(start,start+12,4):body[offset:offset+4]=read(4)
    if not select(0xe02,4):return
    old_count=struct.unpack_from('<H',body,0xc0)[0]
    for i in range(old_count):
        entries=entry_arrays[struct.unpack_from('<Q',body,0xb8)[0]]
        if struct.unpack_from('<Q',entries,i*72+16)[0]:
            reset_resource(body,i,IDENTITY_XYZ,0)
    count=struct.unpack('<I',read(4))[0]
    capacity=struct.unpack_from('<H',body,0xc2)[0]
    if count>capacity:
        seen=set()
        while count>capacity:
            if capacity in seen:raise ValueError('Native uint16 capacity doubling cannot reach requested count')
            seen.add(capacity);capacity=(capacity*2)&0xffff
        grow_entries(body,capacity)
    struct.pack_into('<H',body,0xc0,count&0xffff)
    decoded=0
    for i in range(count):
        pointer=struct.unpack_from('<Q',body,0xb8)[0]
        entry=memoryview(entry_arrays[pointer])[i*72:(i+1)*72]
        if len(entry)!=72:raise ValueError('Retained entry array too short')
        struct.pack_into('<QI',entry,0,body_token,i)
        struct.pack_into('<Q',entry,16,0)
        initialize_pose_transform(entry[24:32],IDENTITY_XYZ,identity_token=identity_token,
            transforms={},allocate=None)
        entry[32:64]=b'\xff'*32
        struct.pack_into('<I',entry,64,0)
        entry[68]=(entry[68]&0xdf)|0x1f
        if not select(0xe04,0,1):
            read_entry(entry,reader,body,pointer+i*72)
            decoded+=1
    struct.pack_into('<I',body,0x110,decoded)
