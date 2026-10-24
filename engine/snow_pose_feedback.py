"""Recovered pose solver-result publication, with external result rows.

Evidence: CENTRAL_IMPULSE.md, Pose solver feedback publication.
Raw bytes preserve result bit patterns; physical interpretation stays unresolved.
"""
import math
import struct
from .snow_pose_solver_counts import HARD_THRESHOLD


def publish_pose_feedback(previous, *, first_flags8, second_flags8, type_id,
                          storage=None, indices=None, result_rows=None):
    """Copy three output words or retain them according to native gates.

    second_flags8=None means no second body. Missing row index is uint32 max.
    Rows are caller-owned 16-byte results; no solve or pointer lookup occurs.
    """
    if len(previous)!=12:raise ValueError('Three previous output words required')
    previous=bytes(previous)
    for flag in (first_flags8,second_flags8):
        if flag is not None and (type(flag) is not int or not 0<=flag<=255):
            raise ValueError('Raw metadata bytes required')
    if first_flags8 is None:raise ValueError('First body required')
    if first_flags8&1 or (second_flags8 is not None and second_flags8&1) or type_id!=2:
        return dict(output=previous,written=[False]*3,mode='skipped')
    if len(storage)!=288 or len(indices)!=3:raise ValueError('Storage and three indices required')
    if any(type(i) is not int or not 0<=i<=0xffffffff for i in indices):raise ValueError('Unsigned row indices required')
    values=[struct.unpack_from('<f',storage,o)[0] for o in (0x8c,0xa0,0xb4)]
    if not all(math.isfinite(v) for v in values):raise ValueError('Finite first-row coefficients required')
    combined=all(v>=HARD_THRESHOLD for v in values) and all(struct.unpack_from('<I',storage,o)[0]==0 for o in (0x80,0x94,0xa8))
    out=bytearray(previous);written=[False]*3
    def row(index):
        r=bytes(result_rows[index])
        if len(r)!=16:raise ValueError('Each result row must contain 16 bytes')
        return r
    if combined:
        if indices[0]!=0xffffffff:
            out[:]=row(indices[0])[:12];written=[True]*3
    else:
        for i,index in enumerate(indices):
            if index!=0xffffffff:out[4*i:4*i+4]=row(index)[:4];written[i]=True
    return dict(output=bytes(out),written=written,mode='combined' if combined else 'separate')
