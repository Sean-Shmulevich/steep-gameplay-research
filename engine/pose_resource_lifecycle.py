"""Resource notification forwarding and known box-resource destruction.

Evidence: docs/reconstruction/LINK_SOLVER.md, Resource notification and box destruction.
"""
import struct


def dispatch_pose_resource_event(manager,descriptor,event,key,*,invoke):
    """Forward through optional manager20 using an isolated16-byte descriptor copy.

    invoke(function_token,descriptor_copy,uint32_event,key) supplies callback code.
    Descriptor padding is copied but has no established semantic interpretation.
    """
    callback=struct.unpack_from('<Q',manager,0x20)[0]
    if not callback:return
    if len(descriptor)<16:raise ValueError('Expected16-byte resource descriptor')
    invoke(callback,bytearray(descriptor[:16]),event&0xffffffff,key)


def destroy_pose_box_resource(token,flags,*,resources,destruction_table,base_table,
                              release_child,release_storage):
    """Known box deleting method; child virtual and resource pool remain services.

    release_child(child_token) supplies virtual+8. release_storage(resource_token)
    supplies the box pool return. Returned token does not establish live storage.
    """
    resource=resources[token]
    struct.pack_into('<Q',resource,0,destruction_table)
    child=struct.unpack_from('<Q',resource,0x20)[0]
    if child:release_child(child)
    struct.pack_into('<Q',resource,0x20,0)
    struct.pack_into('<Q',resource,0,base_table)
    if flags&1 and not flags&4:release_storage(token)
    # flags1+4 calls the observed return-only base stub with size0x50.
    return token
