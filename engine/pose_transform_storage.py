"""Sparse identity transform construction and replacement.

Evidence: docs/reconstruction/LINK_SOLVER.md, Shared identity transform storage.
"""
import struct

TOLERANCE = struct.unpack('<f', struct.pack('<f', 1e-6))[0]


def is_pose_identity_transform(packed_xyz):
    """Native ordered greater-than checks; unordered NaN does not reject identity."""
    if len(packed_xyz) != 48:raise ValueError('Expected four packed XYZ triples')
    values=struct.unpack('<12f',packed_xyz)
    for i,value in enumerate(values):
        if i in (0,4,8):value=struct.unpack('<f',struct.pack('<f',value-1.))[0]
        if abs(value)>TOLERANCE:return False
    return True


def _copy_xyz(target,packed):
    for i in range(4):target[i*16:i*16+12]=packed[i*12:i*12+12]


def initialize_pose_transform(slot,packed_xyz,*,identity_token,transforms,allocate):
    """Construct a transform slot without reading or releasing its previous bytes."""
    if is_pose_identity_transform(packed_xyz):
        struct.pack_into('<Q',slot,0,identity_token)
        return
    token=allocate()
    if not token:raise ValueError('Transform pool returned null')
    struct.pack_into('<Q',slot,0,token)
    _copy_xyz(transforms[token],packed_xyz)


def set_pose_transform(slot,packed_xyz,*,identity_token,transforms,allocate,release):
    """Reuse private storage, allocate from identity, or release back to identity."""
    token=struct.unpack_from('<Q',slot,0)[0]
    identity=is_pose_identity_transform(packed_xyz)
    if token==identity_token:
        if identity:return
        token=allocate()
        if not token:raise ValueError('Transform pool returned null')
        struct.pack_into('<Q',slot,0,token)
    elif identity:
        release(token)
        struct.pack_into('<Q',slot,0,identity_token)
        return
    _copy_xyz(transforms[token],packed_xyz)


def deserialize_retained_pose_resource_entry(entry,reader,body,*,identity_token,
        transforms,allocate_transform,release_transform,**reader_services):
    """Join resource loading with actual transform storage; pool remains supplied."""
    from .pose_resource_entry_decode import deserialize_pose_resource_entry
    deserialize_pose_resource_entry(entry,reader,body,**reader_services,
        set_transform=lambda e,f:set_pose_transform(memoryview(e)[24:32],f,
            identity_token=identity_token,transforms=transforms,
            allocate=allocate_transform,release=release_transform))
