"""Recovered direct-descriptor child attachment over supplied storage.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Direct accessor attachment.
Only the visible direct-descriptor branch is modeled; allocation is supplied.
"""
import struct
from .transform_accessor_initialization import initialize_transform_accessor


def attach_direct_child(accessor, *, owner, child, new_backing=None,
                        initial_transform=None, fallback_holder=None):
    for value in (owner,child):
        if type(value) is not int or not 0<value<2**64:
            raise ValueError('nonnull supplied uint64 identities required')
    created=accessor is None
    if created:
        if new_backing is None or initial_transform is None:
            raise ValueError('new accessor requires supplied backing and transform')
        accessor=initialize_transform_accessor(new_backing,initial_transform,fallback_holder)
    else:
        accessor=bytes(accessor)
        if len(accessor)!=224:raise ValueError('224-byte existing accessor required')
    result=bytearray(accessor)
    if created:struct.pack_into('<Q',result,0x40,owner)
    previous_head=struct.unpack_from('<Q',result,0x48)[0]
    struct.pack_into('<Q',result,0x48,child)
    return dict(accessor=bytes(result),child_next=previous_head,created=created,
                owner_slot_published=created,backlink_written=created)
