"""Sparse physical-body parameter records with explicit pool services.

Evidence: docs/reconstruction/LINK_SOLVER.md, Sparse body parameter setters.
"""
import math
import struct


def _matches(raw, default):
    value = struct.unpack('<f', raw)[0]
    # UCOMISS followed by JE/JNE treats unordered as equality on these paths.
    return math.isnan(value) or value == default


def set_pose_body_scalar(body, value, *, records, allocate, release):
    """Set record1b8's scalar lane; retain vector lanes and raw float bits."""
    if len(value) != 4: raise ValueError('Expected one raw float32 word')
    token = struct.unpack_from('<Q', body, 0x1b8)[0]
    if _matches(value, 0.):
        if not token: return
        record = records[token]
        if all(_matches(record[i:i+4], 0.) for i in (0, 4, 8)):
            release(token)
            struct.pack_into('<Q', body, 0x1b8, 0)
            return
    if not token:
        token = allocate('scalar_vector')
        if not token: raise ValueError('Parameter pool returned null')
        struct.pack_into('<Q', body, 0x1b8, token)
        records[token][:12] = bytes(12)
    records[token][12:16] = value


def set_pose_body_vector(body, value, *, records, allocate, release):
    """Set record1b8's XYZ lanes; retain the scalar lane."""
    if len(value) != 12: raise ValueError('Expected three raw float32 words')
    token = struct.unpack_from('<Q', body, 0x1b8)[0]
    if all(_matches(value[i:i+4], 0.) for i in (0, 4, 8)):
        if not token: return
        if _matches(records[token][12:16], 0.):
            release(token)
            struct.pack_into('<Q', body, 0x1b8, 0)
            return
    if not token:
        token = allocate('scalar_vector')
        if not token: raise ValueError('Parameter pool returned null')
        struct.pack_into('<Q', body, 0x1b8, token)
        records[token][12:16] = bytes(4)
    records[token][:12] = value


def set_pose_body_parameter(body, index, value, *, records, allocate, release):
    """Set one of three record1c0 lanes; all-default records are returned to pool."""
    if index not in (0, 1, 2) or len(value) != 4:
        raise ValueError('Expected lane0..2 and one raw float32 word')
    token = struct.unpack_from('<Q', body, 0x1c0)[0]
    if not token:
        if _matches(value, -1.): return
        token = allocate('triple')
        if not token: raise ValueError('Parameter pool returned null')
        records[token][:12] = struct.pack('<3f', -1., -1., -1.)
        struct.pack_into('<Q', body, 0x1c0, token)
        records[token][index*4:index*4+4] = value
        return
    records[token][index*4:index*4+4] = value
    if all(_matches(records[token][i:i+4], -1.) for i in (0, 4, 8)):
        release(token)
        struct.pack_into('<Q', body, 0x1c0, 0)


def deserialize_retained_physical_pose_body(body, reader, *, buffers, read_base,
                                           records, allocate, release):
    """Compose the physical reader with all five sparse parameter setters."""
    from .pose_body_decode import deserialize_physical_pose_body
    services = dict(records=records, allocate=allocate, release=release)
    deserialize_physical_pose_body(body, reader, buffers=buffers, read_base=read_base,
        set_scalar=lambda b,v: set_pose_body_scalar(b,v,**services),
        set_vector=lambda b,v: set_pose_body_vector(b,v,**services),
        set_parameters=[lambda b,v,i=i: set_pose_body_parameter(b,i,v,**services)
                        for i in range(3)])
