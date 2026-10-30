"""Recovered kind4 command-block loading with explicit reader services.

Evidence: LINK_SOLVER.md, Serialized kind4 command records.
"""
import struct


def deserialize_pose_command_constraint(record,reader,*,read_base,select_block,read_bytes):
    """Read base state then count/single and inline commands.

    select_block(reader,tag,size,scan_limit,required) positions the reader and returns
    whether a block is present. read_bytes(reader,n) advances its cursor and must
    return exactly n bytes. read_base(record,reader) supplies unresolved reference
    and base-field decoding. Services are serial; exceptions do not roll back.
    """
    def read(n):
        data=read_bytes(reader,n)
        if len(data)!=n:raise ValueError('Truncated command block')
        return data
    read_base(record,reader)
    if select_block(reader,0x2607,5,3,True):
        record[0x74:0x78]=read(4)
        record[0x70]=int(read(1)[0]!=0)
    index=0
    while index<struct.unpack_from('<i',record,0x74)[0]:
        if struct.unpack_from('<i',record,0x74)[0]>6:
            raise ValueError('Serialized command count exceeds inline capacity')
        if select_block(reader,0x2608,64,3,True):
            for word in range(16):
                offset=0x78+index*64+word*4
                record[offset:offset+4]=read(4)
        index+=1
