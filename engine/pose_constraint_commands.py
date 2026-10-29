"""Kind4 constraint row builder; LINK_SOLVER.md, Command constraint rows."""
import struct


def build_pose_command_constraint(context, constraint, *, bodies):
    """Append one category24 row and reserve one result record.

    Inputs use retained native storage. Up to six inline 64-byte commands fit the
    912-byte row. Each expands into four XYZ0 vectors and four scalar broadcasts.
    The six-command bound is an authored storage guard, not a native count clamp.
    The builder does not initialize untouched row bytes or the reserved result.
    """
    count = struct.unpack_from('<i',constraint,0x74)[0]
    if count > 6:
        raise ValueError('Command count exceeds retained row capacity')
    if len(constraint) < 0x78+max(0,count)*64:
        raise ValueError('Complete retained commands required')
    u32=lambda off:struct.unpack_from('<I',context,off)[0]
    old_count=u32(0x104)
    row=u32(0x16c)+(((old_count*57+u32(0xa0))&0xffffffff)*16)
    if row+912>len(context):
        raise ValueError('Complete retained row storage required')
    struct.pack_into('<I',context,0x104,(old_count+1)&0xffffffff)
    result=u32(0x180)
    struct.pack_into('<I',context,0x180,(result+1)&0xffffffff)
    struct.pack_into('<I',context,row+4,result)
    first,second=struct.unpack_from('<2Q',constraint,8)
    index=lambda token:struct.unpack_from('<H',bodies[token],0x1c)[0]
    struct.pack_into('<2H',context,row,index(first),index(second) if second else 0)
    context[row+0x20]=constraint[0x70]
    context[row+0x24:row+0x28]=constraint[0x74:0x78]
    order=(2,3,0,1) if constraint[0x59] else (0,1,2,3)
    for i in range(max(0,count)):
        src=0x78+i*64;dst=row+0x30+i*128
        for j,k in enumerate(order):
            context[dst+j*16:dst+j*16+16]=constraint[src+k*12:src+k*12+12]+bytes(4)
        for j in range(4):
            word=constraint[src+48+j*4:src+52+j*4]
            context[dst+64+j*16:dst+80+j*16]=word*4
    return 1
