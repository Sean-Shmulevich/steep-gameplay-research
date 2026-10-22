"""Recovered configured composite-action callback selection.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Composite selector validation.
Child evaluation and mode lookup are explicit caller-supplied dependencies.
No device source, reset order or concurrent mutation policy is inferred.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ChildSample:
    status: int
    payload: bytes  # raw/sample/direction vectors and magnitude, 52 uninterpreted bytes

    def __post_init__(self):
        if type(self.status) is not int or not 0 <= self.status <= 255:
            raise ValueError('status must be uint8')
        if not isinstance(self.payload, bytes) or len(self.payload) != 52:
            raise ValueError('payload must contain exactly 52 bytes')


@dataclass(frozen=True)
class CompositeResult:
    status: int
    payload: bytes
    selected_index: int | None
    visited: tuple[int, ...]


def evaluate_composite(child_count, update_child, mode_at, previous_payload):
    """Configured path only; evaluate children lazily in original call order.

    update_child(index) returns a ChildSample AFTER evaluating that child.
    mode_at(index) supplies a uint32 mode after child evaluation, only for a
    non-final child. Final selection retains the child's full status byte;
    an early mode-zero selection publishes status one. Rejection retains the
    parent's previous payload. The caller owns any preceding zeroing/reset.
    """
    if type(child_count) is not int or not 0 <= child_count <= 65535:
        raise ValueError('child count must be uint16')
    ChildSample(0, previous_payload)
    visited = []
    for index in range(child_count):
        child = update_child(index)
        if not isinstance(child, ChildSample):
            raise TypeError('child evaluator must return ChildSample')
        visited.append(index)
        if index == child_count - 1:
            return CompositeResult(child.status, child.payload, index, tuple(visited))
        mode = mode_at(index)
        if type(mode) is not int or not 0 <= mode < 1 << 32:
            raise ValueError('mode must be uint32')
        if mode == 1 and child.status == 0:
            break
        if mode == 0 and child.status != 0:
            return CompositeResult(1, child.payload, index, tuple(visited))
    return CompositeResult(0, previous_payload, None, tuple(visited))
