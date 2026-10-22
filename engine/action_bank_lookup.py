"""Recovered bank search order; storage and publication are caller-owned.

See MOTION_MEMBERSHIP_OBSERVATION.md, Action-bank search precedence.
A record's map result is supplied explicitly. Missing map entry and an entry
holding a null action pointer have identical control flow in this function.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ActionLayer:
    name: str
    action: Optional[str]
    stop_on_miss: bool = False


@dataclass(frozen=True)
class ActionSelection:
    action: Optional[str]
    visited: tuple
    stopped_on_miss: bool


def select_action(groups: tuple) -> ActionSelection:
    """Three groups in forward order, each searched from last record to first.

    `action` is the resolved result for the requested ID, not an entire map.
    Names are authored opaque identities. No generation, lock or lifetime claim.
    """
    if len(groups) != 3:
        raise ValueError('exactly three groups required')
    visited = []
    for group in groups:
        if len(group) > 65535:
            raise ValueError('group count exceeds uint16')
        for layer in reversed(group):
            if not isinstance(layer, ActionLayer):
                raise ValueError('expected ActionLayer records')
            visited.append(layer.name)
            if layer.action is not None:
                return ActionSelection(layer.action, tuple(visited), False)
            if layer.stop_on_miss:
                return ActionSelection(None, tuple(visited), True)
    return ActionSelection(None, tuple(visited), False)
