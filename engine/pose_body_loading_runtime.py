"""Composition of the known physical-body deserialization layers.

Evidence: docs/reconstruction/LINK_SOLVER.md, Joined physical-body loading.
"""
from .pose_body_base_decode import deserialize_pose_body_base
from .pose_body_resource_array import deserialize_pose_body_resource_array
from .pose_transform_storage import deserialize_retained_pose_resource_entry
from .pose_body_parameters import deserialize_retained_physical_pose_body


def deserialize_known_pose_body(body,reader,*,body_token,buffers,metadata,
        object_tables,fixup_arrays,grow_objects,grow_fixups,entry_arrays,
        identity_token,transforms,allocate_transform,release_transform,
        parameter_records,allocate_parameter,release_parameter,
        reset_resource,grow_entries):
    """Join base, resource-array, entry, transform, motion and parameter decoding.

    Requires an already constructed known-class body and retained dependencies.
    Pools, array growth and virtualD0 reset are explicit services. Does not replay
    references, finalize resource backlinks or register the body with physics.
    """
    references=dict(buffers=buffers,metadata=metadata,object_tables=object_tables,
                    fixup_arrays=fixup_arrays,grow_fixups=grow_fixups)
    def base(b,r):
        deserialize_pose_body_base(b,r,body_token=body_token,
            grow_objects=grow_objects,**references)
    def entry(e,r,b,token):
        deserialize_retained_pose_resource_entry(e,r,b,entry_token=token,
            identity_token=identity_token,transforms=transforms,
            allocate_transform=allocate_transform,release_transform=release_transform,
            **references)
    def middle(b,r):
        deserialize_pose_body_resource_array(b,r,body_token=body_token,buffers=buffers,
            entry_arrays=entry_arrays,identity_token=identity_token,read_base=base,
            reset_resource=reset_resource,grow_entries=grow_entries,read_entry=entry)
    deserialize_retained_physical_pose_body(body,reader,buffers=buffers,read_base=middle,
        records=parameter_records,allocate=allocate_parameter,release=release_parameter)
