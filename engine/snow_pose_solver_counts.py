"""Recovered type-2 pose solver preparation counts.

Evidence: CENTRAL_IMPULSE.md, Pose solver preparation classifier.
Names describe counted branches, not proved original solver row types.
"""
import math
import struct
from reference.central_impulse import f32

HARD_THRESHOLD=f32(1e12)


def pose_solver_counts(storage, second_body_flags16):
    """Return count deltas for six stored rows and a second-body flag class.

    Finite coefficients only. Input storage is the converted 0x120-byte record.
    This performs no solving, allocation or body mutation.
    """
    if len(storage)!=288:raise ValueError('Exact 0x120 storage required')
    if type(second_body_flags16) is not int or not 0<=second_body_flags16<=65535:
        raise ValueError('Unsigned metadata flags required')
    first_hard=first_soft=first_state2=0
    second_hard=second_soft=second_state2=flagged=0
    for i,off in enumerate((0x80,0x94,0xa8,0xbc,0xd0,0xe4)):
        state=struct.unpack_from('<I',storage,off)[0]
        value=struct.unpack_from('<f',storage,off+12)[0]
        if not math.isfinite(value):raise ValueError('Finite row coefficients required')
        hard=value>=HARD_THRESHOLD
        if i<3:
            if state==0:
                first_hard+=int(hard);first_soft+=int(not hard)
            elif state==2:
                first_state2+=1;first_soft+=int(not hard)
        elif state==0:
            second_hard+=int(hard);second_soft+=int(not hard)
        else:
            second_state2+=int(state==2)
            flagged+=int(storage[(0xf8,0x104,0x110)[i-3]]!=0)
    triple=first_hard==3
    return dict(metadata_bit15_set=bool(second_body_flags16&0x8000),
                doubled_rows=2*(second_state2+(0 if triple else first_state2)),
                hard_triple_blocks=int(triple),
                flagged_or_hard_rows=flagged+(0 if triple else first_hard),
                first_soft_rows=0 if triple else first_soft,
                second_hard_rows=second_hard,second_soft_rows=second_soft)
