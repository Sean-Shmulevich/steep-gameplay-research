"""Recovered default action-vector processor; not all configured processors.

Evidence: docs/reconstruction/ACTION_PROCESSOR.md. The native fallback marks a
byte on first use and copies four float32 lanes unchanged. This pure adapter
returns copied state instead of exposing the native output pointer. It does not
select factories, model resource handles, infer input units or normalize input.
"""
import copy
import math
import struct


def _float32_lanes(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError('processor requires four lanes')
    result = []
    for lane in value:
        if isinstance(lane, bool) or not isinstance(lane, (int, float)) or not math.isfinite(lane):
            raise ValueError('processor requires finite numeric lanes')
        try:
            rounded = struct.unpack('<f', struct.pack('<f', lane))[0]
        except (OverflowError, struct.error) as exc:
            raise ValueError('lane exceeds float32 range') from exc
        if not math.isfinite(rounded):
            raise ValueError('lane exceeds float32 range')
        result.append(rounded)
    return result


def initial_state():
    """Relevant initialized fields only; not the complete native object."""
    return {'flag': 0, 'stored': [0., 0., 0., 0.]}


def process_default(value, state=None):
    """Copy four float32 lanes; set a zero byte flag to one, retain nonzero flags.

    Native code can copy any 128-bit payload. This adapter deliberately accepts
    only finite numerical float32 inputs; NaN payload parity is outside its scope.
    Calling this function asserts that the default processor path was selected.
    Bypassed or configured processors must not silently call it as a substitute.
    """
    output = _float32_lanes(value)
    current = initial_state() if state is None else copy.deepcopy(state)
    if not isinstance(current, dict):
        raise ValueError('processor state must be a dictionary')
    flag = current.get('flag')
    if type(flag) is not int or not 0 <= flag <= 255:
        raise ValueError('processor flag must be an unsigned byte')
    current['flag'] = 1 if flag == 0 else flag
    current['stored'] = list(output)
    return {'output': output, 'state': current,
            'evidence': 'recovered default copy kernel; finite float32 adapter',
            'units': 'input-defined; no coordinate or unit conversion'}
