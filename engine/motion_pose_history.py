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


def query_endpoints(state: PoseHistory, local_point: tuple[float, float, float]):
    """Reconstruct the two history-based query endpoints, not body velocity.

    Follows the float32 operations in the endpoint prefix and rotation helper.
    Does not normalize quaternions or divide displacement by time. The query
    shape, orientation, collision execution and resulting hit are not modeled.
    """
    import struct
    def f(x):
        return struct.unpack('<f', struct.pack('<f', x))[0]
    if len(local_point) != 3:
        raise ValueError('local point needs three components')
    v = tuple(f(x) for x in local_point)
    def endpoint(pose):
        px, py, pz, _, x, y, z, w = struct.unpack('<8f', pose)
        q = (x, y, z)
        products = [f(q[i]*v[i]) for i in range(3)]
        dot = f(products[0] + f(products[1] + products[2]))
        cross = [f(f(q[(i+1)%3]*v[(i+2)%3]) -
                   f(q[(i+2)%3]*v[(i+1)%3])) for i in range(3)]
        scale = f(f(w*w) - 0.5)
        return tuple(f(p + f(2.0*f(f(f(dot*q[i]) + f(cross[i]*w)) +
                                   f(scale*v[i]))))
                     for i, p in enumerate((px, py, pz)))
    return endpoint(state.previous), endpoint(state.current)
