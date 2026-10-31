"""Body-event listener append and first-match removal.

Evidence: docs/reconstruction/LINK_SOLVER.md, Body listener registration and removal.
"""
import struct


def register_pose_body_listener(callback,*,get_registry,listener_arrays,grow,padding):
    """Append enabled callback; seven native stack-padding bytes are explicit input."""
    if len(padding)!=7:raise ValueError('Expected seven opaque padding bytes')
    registry=get_registry()
    count,capacity=struct.unpack_from('<II',registry,8)
    if count==capacity:
        capacity=capacity*2 if capacity else 8
        if capacity>0xffffffff//16:raise ValueError('Listener allocation exceeds uint32 byte size')
        grow(registry,capacity)
    count=struct.unpack_from('<I',registry,8)[0]
    rows=listener_arrays[struct.unpack_from('<Q',registry,0)[0]]
    rows[count*16:count*16+16]=struct.pack('<QB',callback,1)+bytes(padding)
    struct.pack_into('<I',registry,8,(count+1)&0xffffffff)


def remove_pose_body_listener(callback,*,tls,get_registry,listener_arrays):
    """Remove first matching callback or disable it while dispatch is active.

    Missing membership raises an authored KeyError before writes instead of native
    invalid-index access. Disabled rows participate in the same first-match search.
    """
    registry=get_registry()
    count=struct.unpack_from('<I',registry,8)[0]
    if count>0x7fffffff:raise ValueError('Listener count outside retained signed domain')
    rows=listener_arrays[struct.unpack_from('<Q',registry,0)[0]]
    index=next((i for i in range(count) if struct.unpack_from('<Q',rows,16*i)[0]==callback),None)
    if index is None:raise KeyError('Body listener is not registered')
    offset=index*16
    if tls[0x27bd]:
        rows[offset+8]=0
        tls[0x27bc]=1
    else:
        struct.pack_into('<I',registry,8,count-1)
        length=(count-1-index)*16
        rows[offset:offset+length]=bytes(rows[offset+16:offset+16+length])
