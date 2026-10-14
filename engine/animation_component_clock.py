"""Recovered KinoComponent interval source selection, before interface update.

World clock ownership and relation to physics substeps remain unresolved.
"""
import math
import struct


def component_interval(*, component_flags, owner_present, world_present,
                       owner_flags, ordinary_interval, alternate_interval):
    """Select the copied float32 interval; disabled/missing paths produce +0.

    Names ordinary/alternate distinguish two source fields without assigning
    either a gameplay clock domain. Finite input rejection is an adapter guard.
    """
    if type(component_flags) is not int or not 0 <= component_flags < 256:
        raise ValueError('component_flags must be uint8')
    if type(owner_flags) is not int or not 0 <= owner_flags < 1 << 64:
        raise ValueError('owner_flags must be uint64')
    if type(owner_present) is not bool or type(world_present) is not bool:
        raise ValueError('presence must be bool')
    if component_flags & 2 or not owner_present or not world_present:
        return 0.0
    value = alternate_interval if owner_flags & (1 << 58) else ordinary_interval
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('selected interval must be finite')
    try:
        result = struct.unpack('<f', struct.pack('<f', value))[0]
    except OverflowError as exc:
        raise ValueError('selected interval overflows float32') from exc
    if not math.isfinite(result):
        raise ValueError('selected interval overflows float32')
    return result


def dispatch_component_update(*, interface_ready, auxiliary_present, auxiliary_ready):
    """Recovered local call gates, after interval selection and before slot 0x50.

    This does not model work performed on either non-dispatch path.
    """
    values = (interface_ready, auxiliary_present, auxiliary_ready)
    if any(type(value) is not bool for value in values):
        raise ValueError('call gates must be bool')
    return all(values)
