"""Known-body resource transform update and deferred-refresh flags.

Evidence: docs/reconstruction/LINK_SOLVER.md, Known-body resource transform reset.
"""
import struct
from .pose_transform_storage import set_pose_transform


def update_pose_resource_transform(body,index,frame,update_now,*,entry_arrays,
        identity_token,transforms,allocate,release,metadata,
        refresh_bounds,refresh_first,refresh_second):
    """Known virtualD0; optional derived refresh calls remain explicit services."""
    index &= 0xffffffff
    immediate=bool(update_now&255)
    entries=entry_arrays[struct.unpack_from('<Q',body,0xb8)[0]]
    slot=memoryview(entries)[index*72+24:index*72+32]
    set_pose_transform(slot,frame,identity_token=identity_token,transforms=transforms,
                       allocate=allocate,release=release)
    if immediate:refresh_bounds(body,0)
    body[0xb0]=int(not immediate)
    entries=entry_arrays[struct.unpack_from('<Q',body,0xb8)[0]]
    if not entries[index*72+0x44]&1:return
    if immediate and not metadata[struct.unpack_from('<Q',body,0x30)[0]][0x52]&8:
        refresh_first(body)
        refresh_second(body)
        body[0xaa]&=0xef
    else:body[0xaa]|=0x10


def reset_known_pose_resource(body,index,frame,update_now,*,entry_arrays,
        identity_token,transforms,allocate,release):
    """Bind the loader's deferred-refresh call; does not release the resource."""
    if update_now&255:raise ValueError('Loader reset binding requires deferred refresh')
    update_pose_resource_transform(body,index,frame,update_now,entry_arrays=entry_arrays,
        identity_token=identity_token,transforms=transforms,allocate=allocate,release=release,
        metadata={},refresh_bounds=None,refresh_first=None,refresh_second=None)
