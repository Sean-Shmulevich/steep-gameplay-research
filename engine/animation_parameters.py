"""Recovered lazy parameter preparation with an explicit reset boundary.

The caller supplies group mapping, callbacks and update completion. No device
input mapping, original callback implementation or frame cadence is inferred.
"""
from dataclasses import dataclass


@dataclass
class ParameterGroup:
    callback: object
    prepared: bool = False


def prepare_parameter(index, mapping, groups, *, context=None):
    """Evaluate a mapped group once until reset; flag changes after callback returns.

    Context is a caller-owned stand-in for the native optional owner subobject.
    Returns whether a callback was invoked, an adapter diagnostic.
    """
    if type(index) is not int or not 0 <= index < len(mapping):
        raise ValueError('parameter index out of bounds')
    group_index = mapping[index]
    if type(group_index) is not int or not 0 <= group_index <= 255:
        raise ValueError('parameter group mapping must be uint8')
    if group_index == 255:
        return False
    if group_index >= len(groups):
        raise ValueError('parameter group index out of bounds')
    group = groups[group_index]
    if not isinstance(group, ParameterGroup):
        raise ValueError('expected ParameterGroup')
    if group.prepared:
        return False
    if not callable(group.callback):
        raise ValueError('unprepared group has no callback')
    group.callback(context)
    group.prepared = True
    return True


def reset_parameter_groups(groups, *, enabled):
    """Clear all group flags only at a caller-supplied reset boundary.

    Enabled is not synonymous with a render frame or physics substep. Native
    update branching is documented separately; the adapter does not choose it.
    """
    if type(enabled) is not bool:
        raise ValueError('reset boundary must be explicit bool')
    if not enabled:
        return
    groups = tuple(groups)
    if any(not isinstance(group, ParameterGroup) for group in groups):
        raise ValueError('expected ParameterGroup')
    for group in groups:
        group.prepared = False
