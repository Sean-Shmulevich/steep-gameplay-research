"""Recovered low-motion duration accumulation and metadata state update.

Evidence: LINK_SOLVER.md, Body low-motion timer and threshold overrides.
"""
import math
import struct
from reference.central_impulse import f32


def update_pose_body_quiet_state(body, metadata, *, scalar, duration_threshold,
                                 linear_threshold, angular_threshold, overrides=None):
    """Update raw body+28 and metadata+53 with finite retained inputs.

    Overrides, when supplied, are linear/angular/duration values from body+1c0.
    Each exact -1.0 selects the caller default. No time unit, group activation,
    virtual callback, allocation or live pointer handling is supplied here.
    """
    if len(body)<0x1b8 or len(metadata)<0x54:
        raise ValueError('Complete retained body and metadata required')
    def finite(x):
        value=f32(x)
        if not math.isfinite(value):raise ValueError('Finite scalar required')
        return value
    defaults=list(map(finite,(linear_threshold,angular_threshold,duration_threshold)))
    if overrides is not None:
        if len(overrides)!=3:raise ValueError('Three override fields required')
        defaults=[d if v==-1.0 else v for d,v in zip(defaults,map(finite,overrides))]
    linear,angular,duration=defaults
    def squared(off):
        v=list(map(finite,struct.unpack_from('<3f',body,off)))
        return f32(f32(f32(v[0]*v[0])+f32(v[1]*v[1]))+f32(v[2]*v[2]))
    if body[0xaa]&2 or squared(0x1a0)>=f32(linear*linear) or squared(0x1ac)>=f32(angular*angular):
        struct.pack_into('<I',body,0x28,0)
        metadata[0x53]&=0xf0
        return
    timer=f32(finite(scalar)+finite(struct.unpack_from('<f',body,0x28)[0]))
    struct.pack_into('<f',body,0x28,timer)
    if timer>duration:
        metadata[0x53]=(metadata[0x53]&0xf1)|1


def reset_pose_body_quiet_state(body, metadata):
    """Constructor-selected slot28 resets timer/state while preserving motion.

    Evidence: LINK_SOLVER.md, Body reset and ordinary-group reactivation.
    """
    if len(body)<0x2c or len(metadata)<0x54:
        raise ValueError('Retained timer and metadata required')
    metadata[0x53]&=0xf0
    body[0x28:0x2c]=bytes(4)
