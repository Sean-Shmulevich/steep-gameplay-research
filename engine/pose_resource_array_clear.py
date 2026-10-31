"""Known-body reverse resource cleanup and transform release.

Evidence: docs/reconstruction/LINK_SOLVER.md, Resource-array destruction pass.
"""
import struct


def clear_pose_body_resources(body,*,body_token,entry_arrays,resources,
                              identity_token,notify,destroy,release_transform):
    """Notify and destroy nonnull resources in reverse index order.

    notify(body_token,index,resource_key,1) supplies18b74b0 registry dispatch.
    destroy(resource_token,1) supplies the resource's deleting virtual method.
    Null-resource entries skip transform cleanup as the original routine does.
    """
    count=struct.unpack_from('<H',body,0xc0)[0]
    for index in range(count-1,-1,-1):
        offset=index*72
        entries=entry_arrays[struct.unpack_from('<Q',body,0xb8)[0]]
        resource=struct.unpack_from('<Q',entries,offset+16)[0]
        if not resource:continue
        key=struct.unpack_from('<Q',resources[resource],0x10)[0]
        notify(body_token,index,key,1)
        destroy(resource,1)
        entries=entry_arrays[struct.unpack_from('<Q',body,0xb8)[0]]
        struct.pack_into('<Q',entries,offset+16,0)
        remaining=struct.unpack_from('<I',body,0x110)[0]
        struct.pack_into('<I',body,0x110,(remaining-1)&0xffffffff)
        entries=entry_arrays[struct.unpack_from('<Q',body,0xb8)[0]]
        transform=struct.unpack_from('<Q',entries,offset+24)[0]
        if transform!=identity_token:
            release_transform(transform)
            struct.pack_into('<Q',entries,offset+24,identity_token)
    struct.pack_into('<H',body,0xc0,0)
