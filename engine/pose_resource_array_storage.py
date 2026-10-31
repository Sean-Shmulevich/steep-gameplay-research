"""Small-buffer storage policy for72-byte body resource entries.

Evidence: docs/reconstruction/LINK_SOLVER.md, Inline resource-array storage.
"""
import struct


def resize_pose_resource_array(body,requested,*,body_token,entry_arrays,
                               allocate,reallocate,release):
    """Resize bodyb8/c0/c2, using inline storage at bodyc8 for capacity0/1.

    allocate(bytes,alignment,tag) and reallocate(token,bytes,alignment,tag) must
    publish retained buffers before returning. release(token) supplies allocator
    free. These operations do not destroy entries or resources. uint16 requested
    capacity is the supported retained domain; out-of-domain values raise.
    """
    if not 0<=requested<=0xffff:raise ValueError('Expected uint16 resource capacity')
    capacity=struct.unpack_from('<H',body,0xc2)[0]
    if requested==capacity:return
    inline_token=body_token+0xc8
    inline=memoryview(body)[0xc8:0x110]
    pointer=struct.unpack_from('<Q',body,0xb8)[0]
    if requested>1:
        if pointer==inline_token:
            token=allocate(requested*72,16,0x4c)
            if not token:raise ValueError('Resource allocator returned null')
            count=struct.unpack_from('<H',body,0xc0)[0]
            if count>1:raise ValueError('Inline resource count exceeds retained storage')
            struct.pack_into('<Q',body,0xb8,token)
            entry_arrays[token][:count*72]=inline[:count*72]
        else:
            token=reallocate(pointer,requested*72,16,0x4c)
            if not token:raise ValueError('Resource reallocator returned null')
            struct.pack_into('<Q',body,0xb8,token)
        struct.pack_into('<H',body,0xc2,requested)
    else:
        if pointer!=inline_token:
            if requested:inline[:72]=entry_arrays[pointer][:72]
            release(struct.unpack_from('<Q',body,0xb8)[0])
            struct.pack_into('<Q',body,0xb8,inline_token)
        struct.pack_into('<H',body,0xc2,1)
    if struct.unpack_from('<H',body,0xc0)[0]>requested:
        struct.pack_into('<H',body,0xc0,requested)
    entry_arrays[inline_token]=inline
