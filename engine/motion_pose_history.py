"""Local pose-history branch of preparation B, not an animation evaluator.

Evidence: docs/reconstruction/MOTION_MEMBERSHIP_OBSERVATION.md,
'Preparation B pose history'. Call cadence and source lookup remain external.
The opaque 32-byte poses are two four-lane values; this module preserves bits
and requires the caller to supply the final pose after any coordinate transform.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PoseHistory:
    current: bytes
    previous: bytes
    count: int

    def __post_init__(self):
        for value in (self.current, self.previous):
            if not isinstance(value, bytes) or len(value) != 32:
                raise ValueError('pose must be exactly 32 immutable bytes')
        if type(self.count) is not int or not 0 <= self.count <= 255:
            raise ValueError('count must be an unsigned byte')

    @property
    def downstream_guard_eligible(self) -> bool:
        """Eligibility to call a guard, not proof of pose freshness or actuation."""
        return self.count >= 2


def advance_pose_history(
    state: PoseHistory,
    source: Literal['missing_provider', 'missing_key', 'valid'],
    resolved_pose: bytes | None = None,
) -> PoseHistory:
    """Apply one observed preparation invocation, with no assumed tick duration.

    Missing provider preserves history. Missing key clears only the count.
    A valid sample shifts current to previous and increments counts below two;
    values already above two are preserved, matching the byte comparison.
    Input validation and immutable return objects are reconstruction API choices.
    """
    if source not in ('missing_provider', 'missing_key', 'valid'):
        raise ValueError('unknown source result')
    if source == 'valid':
        return PoseHistory(resolved_pose, state.current,
                           state.count + 1 if state.count < 2 else state.count)
    if resolved_pose is not None:
        raise ValueError('missing source cannot supply a pose')
    if source == 'missing_key':
        return PoseHistory(state.current, state.previous, 0)
    return state
