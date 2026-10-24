"""Recovered group construction and visible pool-return publication.

Evidence: CENTRAL_IMPULSE.md, Group reconstruction after pool reuse.
"""
import struct


def construct_pose_group(previous_storage, *, token, index, table):
    """Return 168 bytes with only constructor-written fields replaced.

    token/table are explicit uint64 identities. This function does not allocate,
    publish context membership, resolve native tables or pin an object lifetime.
    """
    if len(previous_storage)!=168:
        raise ValueError('Exact 168-byte group storage required')
    for name,value,limit in [('token',token,2**64),('table',table,2**64),
                             ('index',index,2**32)]:
        if type(value) is not int or not 0<=value<limit:
            raise ValueError(f'{name} must fit its unsigned native width')
    out=bytearray(previous_storage)
    struct.pack_into('<I',out,0xc,index)
    struct.pack_into('<Q',out,0,table)
    struct.pack_into('<QII',out,0x10,(token+0x20)&0xffffffffffffffff,0,4)
    struct.pack_into('<QII',out,0x40,(token+0x50)&0xffffffffffffffff,0,8)
    struct.pack_into('<QIIH',out,0x90,0,0,0,0)
    return bytes(out)


def return_pose_group_storage(pool, token, *, write_next):
    """Visible serial publication after cleanup and the first protected call.

    write_next(token, previous_head) overwrites the retired object's first word.
    No destructor, lock, membership check or duplicate-return guard is supplied.
    """
    previous=pool['free_head']
    write_next(token,previous)
    pool['used']=(pool['used']-1)&0xffffffff
    pool['free_head']=token
