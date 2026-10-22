"""Deferred skeleton work dispatch, with evaluation/application kept external.

Evidence: CENTRAL_IMPULSE.md, Child preparation consumes deferred work.
Scalar input/output use IEEE binary32 bits to preserve NaNs and signed zero.
work_count is the supplied count after the opaque evaluation call, if any.
"""
import struct


def plan_preparation(scalar_bits, use_primary, component_flags, work_count, pending):
    if type(scalar_bits) is not int or not 0 <= scalar_bits < 2**32:
        raise ValueError('uint32 scalar bits required')
    if type(use_primary) is not bool:
        raise ValueError('boolean bank selection required')
    if type(component_flags) is not int or not 0 <= component_flags <= 65535:
        raise ValueError('uint16 component flags required')
    if work_count is not None and (type(work_count) is not int or not 0 <= work_count <= 65535):
        raise ValueError('absent or uint16 work count required')
    if type(pending) is not int or not 0 <= pending <= 255:
        raise ValueError('uint8 pending required')
    scalar = struct.unpack('<f', struct.pack('<I', scalar_bits))[0]
    calls = []
    if scalar >= 0:  # ordered comparison; NaN skips, negative zero participates
        calls.append('evaluate_primary' if use_primary else 'evaluate_current')
        scalar_bits = 0xbf800000
    mask = (component_flags >> 3) & 7
    cleared = False
    if work_count:
        if mask:
            calls.extend(['lock', 'apply_primary' if use_primary else 'apply_current',
                          'process_primary' if use_primary else 'process_current', 'unlock'])
            pending |= 1
        else:
            calls.append('clear_work')
            work_count = 0
            cleared = True
    return dict(calls=calls, scalar_bits=scalar_bits, pending=pending,
                work_count=work_count, counters_cleared=cleared, mask=mask)
