"""Recovered direct motion update for the worker's non-solver branch.

Evidence: LINK_SOLVER.md, Free-motion worker branch.
"""
import math
import struct
from reference.central_impulse import f32


def advance_pose_free_motion(body_tokens, *, bodies, metadata, scalar, vector,
                              damping_records=None, damping_response=None):
    """Update raw linear/angular motion in retained array order.

    Repeated body identities update repeatedly. Damping's four-lane library
    response remains explicit. Constant finite scalar/vector, normal callbacks
    and retained identities define this contract; transforms are not integrated.
    """
    def finite(value):
        value=f32(value)
        if not math.isfinite(value):raise ValueError('Finite motion arithmetic required')
        return value
    s=finite(scalar)
    if len(vector)!=3:raise ValueError('Three external-vector components required')
    delta=[finite(s*finite(v)) for v in vector]
    for i in range(len(body_tokens)):
        body=bodies[body_tokens[i]]
        meta=metadata[struct.unpack_from('<Q',body,0x30)[0]]
        if meta[0x52]&8:continue
        damping=struct.unpack_from('<Q',body,0x1b8)[0]
        multiplier=[1.]*4
        if damping and s!=0:
            if damping_records is None or damping_response is None:
                raise ValueError('Reached damping requires record and response services')
            record=damping_records[damping]
            if len(record)!=4:raise ValueError('Four damping components required')
            base=[finite(1.-finite(v)) for v in record]
            multiplier=list(map(finite,damping_response(base,s)))
            if len(multiplier)!=4:raise ValueError('Four damping response components required')
        applied=[0.]*3 if body[0xaa]&8 else delta
        linear=struct.unpack_from('<3f',body,0x1a0)
        angular=struct.unpack_from('<3f',body,0x1ac)
        linear=[finite(finite(finite(v)+d)*m) for v,d,m in zip(linear,applied,multiplier)]
        angular=[finite(finite(v)*multiplier[3]) for v in angular]
        struct.pack_into('<6f',body,0x1a0,*linear,*angular)
