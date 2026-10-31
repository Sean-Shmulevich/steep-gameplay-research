"""Known physical-body destructor layers, excluding outer object storage return.

Evidence: docs/reconstruction/LINK_SOLVER.md, Known-body destructor layers.
"""
import struct
from .pose_resource_array_storage import resize_pose_resource_array


def destroy_known_pose_body(body,*,body_token,physical_table,resource_body_table,
        base_table,final_table,entry_arrays,release_parameter,clear_resources,
        release_entries,notify_body,release_metadata):
    """Destroy owned state in recovered order; outer deleting wrapper is separate.

    release_parameter(kind,token) supplies the corresponding pool return.
    clear_resources(body) can bind the reconstructed reverse resource cleanup.
    notify_body(body,event10) supplies listener dispatch; it may mutate metadata30.
    Metadata is captured after notification and is not cleared after pool return.
    """
    struct.pack_into('<Q',body,0,physical_table)
    for offset,kind in ((0x1b8,'scalar_vector'),(0x1c0,'triple')):
        token=struct.unpack_from('<Q',body,offset)[0]
        if token:
            release_parameter(kind,token)
            struct.pack_into('<Q',body,offset,0)
    struct.pack_into('<Q',body,0,resource_body_table)
    clear_resources(body)
    resize_pose_resource_array(body,0,body_token=body_token,entry_arrays=entry_arrays,
        allocate=None,reallocate=None,release=release_entries)
    struct.pack_into('<Q',body,0xb8,0)
    struct.pack_into('<H',body,0xc2,0)
    struct.pack_into('<Q',body,0,base_table)
    notify_body(body,10)
    token=struct.unpack_from('<Q',body,0x30)[0]
    release_metadata(token)
    struct.pack_into('<Q',body,0,final_table)
