"""Recovered settings-to-context initialization and reciprocal scalar relation.

Evidence: LINK_SOLVER.md, Solver context settings initialization.
"""
import math
import struct
from reference.central_impulse import f32


def initialize_pose_solver_settings(context,settings,*,scalar,group_token):
    """Write recovered header fields while preserving all row/layout storage.

    Settings are at least64 bytes. Scalar and reciprocal must be finite/nonzero.
    Raw copied words are not interpreted as floats. Source/destination overlap,
    native exceptional division and pointer lifetime are outside this contract.
    """
    if len(context)<0x3c or len(settings)<0x40:raise ValueError('Retained context header and64-byte settings required')
    if type(group_token) is not int or not 0<=group_token<=0xffffffffffffffff:raise ValueError('Raw uint64 group token required')
    value=f32(scalar)
    if value==0 or not math.isfinite(value):raise ValueError('Finite nonzero scalar required')
    inverse=f32(1.0/value)
    if not math.isfinite(inverse):raise ValueError('Finite reciprocal required')
    struct.pack_into('<2f',context,0xc,inverse,value)
    for source,target in ((0x2c,0x14),(0x30,0x18),(0x1c,0x1c),(0x18,0x20),
                          (0x34,0x24),(0x38,0x28),(0x3c,0x2c),(8,0),(12,4),(16,8)):
        context[target:target+4]=settings[source:source+4]
    struct.pack_into('<Q',context,0x30,group_token)
    old=struct.unpack_from('<I',context,0x38)[0]
    mode=struct.unpack_from('<I',settings,0x24)[0]&3
    iterations=struct.unpack_from('<H',settings,0x28)[0]&0x3fff
    secondary_iterations=struct.unpack_from('<H',settings,0x2a)[0]&0x7ff
    flags=(old&0x80000000)|mode|((settings[0x21]&1)<<29)|((settings[0x14]&1)<<30)|(secondary_iterations<<16)|(iterations<<2)
    struct.pack_into('<I',context,0x38,flags)
