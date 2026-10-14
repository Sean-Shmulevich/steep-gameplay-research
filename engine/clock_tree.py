"""Independent immutable adapter for recovered clock updates.

Evidence and excluded concurrency semantics: docs/reconstruction/CLOCK_TREE.md.
"""
from dataclasses import dataclass, replace
from .world_clock import clock_interval, _f32


def _signed32(value):
    return ((value + (1 << 31)) % (1 << 32)) - (1 << 31)


@dataclass(frozen=True)
class ClockState:
    interval: float = 0.0
    previous_interval: float = 0.0
    reciprocal: float = 0.0
    hold_count: int = 0
    previous_hold_count: int = 0
    pending_holds: int = 0
    scale_enabled: bool = False
    secondary_enabled: bool = False
    scale: float = 1.0
    secondary_scale: float = 1.0
    use_parent_previous: bool = False
    ticks: int = 0
    accumulated_ticks: int = 0
    divided_ticks: int = 0
    counter: int = 0
    toggle: int = 0
    children: tuple = ()


def request_hold(state, *, release=False):
    """Model one pending atomic +/-1 operation; this Python adapter is not atomic."""
    if not isinstance(state, ClockState) or type(release) is not bool:
        raise ValueError('ClockState and bool release required')
    if type(state.pending_holds) is not int or not -(1 << 31) <= state.pending_holds < (1 << 31):
        raise ValueError('pending holds must be signed int32')
    return replace(state, pending_holds=_signed32(state.pending_holds + (-1 if release else 1)))


def advance_clock(state, input_ms, *, accumulate=True):
    """Return updated state/tree. No native lock, scheduler or timer is controlled.

    Only an acyclic, unshared tree of at most 256 nodes/depth 64 is accepted.
    This adapter restriction avoids inventing ownership for arbitrary pointers.
    """
    if type(accumulate) is not bool: raise ValueError('accumulate must be bool')
    seen = set()
    def visit(node, elapsed, depth):
        if not isinstance(node, ClockState) or not isinstance(node.children, tuple):
            raise ValueError('ClockState with tuple children required')
        if id(node) in seen or len(seen) >= 256 or depth > 64:
            raise ValueError('clock tree is shared, cyclic or exceeds limits')
        seen.add(id(node))
        if type(node.use_parent_previous) is not bool:
            raise ValueError('child source flag must be bool')
        for value, width in ((node.counter,32),(node.toggle,32),(node.accumulated_ticks,64)):
            if type(value) is not int or not 0 <= value < (1 << width):
                raise ValueError('clock counter exceeds unsigned width')
        local = clock_interval(input_ms=elapsed, previous_interval=node.interval,
                               hold_count=node.hold_count,pending_holds=node.pending_holds,
                               scale_enabled=node.scale_enabled,secondary_enabled=node.secondary_enabled,
                               scale=node.scale,secondary_scale=node.secondary_scale)
        # Keep the pre-division processed value: divide then multiply can round differently.
        processed = _f32(elapsed)
        if local['hold_count'] > 0: processed = 0.0
        elif node.scale_enabled:
            processed = _f32(processed * _f32(node.scale))
            if node.secondary_enabled: processed = max(_f32(processed * _f32(node.secondary_scale)), _f32(.005))
        elif node.secondary_enabled: processed = _f32(processed * _f32(node.secondary_scale))
        total = (node.accumulated_ticks + local['ticks']) & ((1 << 64)-1) if accumulate else node.accumulated_ticks
        children = tuple(visit(child, _f32(local['previous_interval'] * 1000.0) if child.use_parent_previous else processed, depth+1) for child in node.children)
        return replace(node, **local, accumulated_ticks=total,
                       divided_ticks=total//30 if accumulate else node.divided_ticks,
                       counter=(node.counter+1)&0xffffffff if accumulate else node.counter,
                       toggle=node.toggle ^ (1 if local['hold_count'] <= 0 else 0),children=children)
    return visit(state, input_ms, 0)
