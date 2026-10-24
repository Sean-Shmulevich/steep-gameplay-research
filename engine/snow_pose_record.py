"""Recovered pose-record conversion and frame-pair ordering.

Evidence: CENTRAL_IMPULSE.md, Pose record submission boundary.
Byte buffers are supplied independent records; no game payload is bundled.
"""


def pack_pose_record(source, initialized_destination, vector_mask, swapped=False):
    """Pack 0x100 source bytes into supplied 0x120 initialized storage.

    The runtime 16-byte bit mask is an explicit dependency. Preserve untouched
    padding. Optional swap exchanges only the first two
    64-byte frame blocks, as the submission wrapper does after conversion.
    """
    if len(source)!=0x100 or len(initialized_destination)!=0x120:
        raise ValueError('Exact 0x100 source and 0x120 destination sizes required')
    if len(vector_mask)!=16:raise ValueError('Exact 16-byte vector mask required')
    vector_mask=bytes(vector_mask)
    if type(swapped) is not bool:raise ValueError('Explicit swap decision required')
    source=bytes(source);out=bytearray(initialized_destination)
    for i in range(8):
        out[i*16:i*16+16]=bytes(a & b for a,b in zip(source[i*12:i*12+16],vector_mask))
    out[0x80:0xf8]=source[0x60:0xd8]
    for src,dst,size in ((0xd8,0xf8,1),(0xd9,0xf9,1),(0xdc,0xfc,4),(0xe0,0x100,4),
                         (0xe4,0x104,1),(0xe5,0x105,1),(0xe8,0x108,4),(0xec,0x10c,4),
                         (0xf0,0x110,1),(0xf1,0x111,1),(0xf4,0x114,4),(0xf8,0x118,4),(0xfc,0x11c,1)):
        out[dst:dst+size]=source[src:src+size]
    if swapped:out[:0x80]=out[0x40:0x80]+out[:0x40]
    return bytes(out)


def pose_submission_notification(request_byte):
    """Wrapper converts only byte exactly 1 to the downstream notification flag."""
    if not isinstance(request_byte,int) or not 0<=request_byte<=255:
        raise ValueError('Raw uint8 request required')
    return request_byte==1


def store_pose_record(packed, previous_storage):
    """Copy defined fields, preserving destination padding; independent buffers."""
    if len(packed)!=0x120 or len(previous_storage)!=0x120:
        raise ValueError('Exact 0x120 record sizes required')
    packed=bytes(packed);out=bytearray(previous_storage)
    out[:0xfa]=packed[:0xfa]
    for start,end in ((0xfc,0x106),(0x108,0x112),(0x114,0x11d)):
        out[start:end]=packed[start:end]
    return bytes(out)


def prepare_pose_submission(source, previous_storage, vector_mask,
                            swap_byte, request_byte):
    """Return stored fields and notification intent, without executing services.

    Temporary constructor values do not survive into copied fields: conversion
    overwrites all of them. Destination padding survives from previous storage.
    Live object resolution, locking and notification effects remain external.
    """
    if not isinstance(swap_byte,int) or not 0<=swap_byte<=255:
        raise ValueError('Raw uint8 swap flag required')
    notify=pose_submission_notification(request_byte)
    packed=pack_pose_record(source,bytes(0x120),vector_mask,swap_byte!=0)
    return dict(storage=store_pose_record(packed,previous_storage),notify=notify)
