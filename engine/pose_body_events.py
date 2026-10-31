"""Body-event listener dispatch and deferred disabled-listener compaction.

Evidence: docs/reconstruction/LINK_SOLVER.md, Body-event listener dispatch.
"""
import struct


def dispatch_pose_body_event(body_token,event,*,tls,get_registry,listener_arrays,invoke):
    """Dispatch enabled16-byte listeners and compact disabled rows when requested.

    get_registry() supplies the current descriptor with pointer0/count8. Callback
    invoke(function_token,body_token,uint32_event) may change the registry. TLS
    byte27bd marks dispatch; byte27bc requests compaction. No snapshot isolation,
    recursive-depth protection or exception cleanup is invented.
    """
    registry=get_registry()
    tls[0x27bd]=1
    index=0
    while index<struct.unpack_from('<I',registry,8)[0]:
        rows=listener_arrays[struct.unpack_from('<Q',registry,0)[0]]
        offset=index*16
        if rows[offset+8]:
            callback=struct.unpack_from('<Q',rows,offset)[0]
            invoke(callback,body_token,event&0xffffffff)
            registry=get_registry()
        index+=1
    tls[0x27bd]=0
    if not tls[0x27bc]:return
    count=struct.unpack_from('<I',registry,8)[0]
    # Native loop treats count-1 as signed32. Large nonretained counts are invalid.
    if count>0x7fffffff:raise ValueError('Listener count outside retained signed domain')
    for index in range(count-1,-1,-1):
        rows=listener_arrays[struct.unpack_from('<Q',registry,0)[0]]
        offset=index*16
        if not rows[offset+8]:
            remaining=struct.unpack_from('<I',registry,8)[0]-1
            struct.pack_into('<I',registry,8,remaining)
            length=(remaining-index)*16
            rows[offset:offset+length]=bytes(rows[offset+16:offset+16+length])
            registry=get_registry()
    tls[0x27bc]=0
