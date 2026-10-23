"""Local pose-history branch of preparation B, not an animation evaluator.

Evidence: docs/reconstruction/MOTION_MEMBERSHIP_OBSERVATION.md,
'Preparation B pose history'. Call cadence and source lookup remain external.
The opaque 32-byte poses are two four-lane values; this module preserves bits
and accepts the final pose from transform_provider_pose or another qualified source.
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


def transform_provider_pose(pose: bytes, provider: bytes, *, already_world: bool) -> bytes:
    """Resolve preparation B's provider transform before advancing history.

    Both poses contain position XYZW then quaternion XYZW, 32 bytes each.
    Provider bit26 selects already_world; that branch preserves pose bits.
    Otherwise compose provider rotation * local rotation and rotate/translate
    local position. No quaternion normalization. Finite float32 arithmetic only;
    reject overflow rather than claim native exceptional-value equivalence.
    Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Provider pose transform.
    """
    import math
    import struct
    if type(already_world) is not bool:
        raise ValueError('explicit provider transform flag required')
    if not isinstance(pose, bytes) or len(pose) != 32:
        raise ValueError('pose must be 32 bytes')
    if already_world:
        return pose
    if not isinstance(provider, bytes) or len(provider) != 32:
        raise ValueError('provider transform must be 32 bytes')
    def f(x):
        try: value=struct.unpack('<f',struct.pack('<f',x))[0]
        except (OverflowError,struct.error) as exc:raise ValueError('float32 overflow') from exc
        if not math.isfinite(value):raise ValueError('finite float32 domain required')
        return value
    p=struct.unpack('<8f',pose); t=struct.unpack('<8f',provider)
    if not all(math.isfinite(x) for x in (*p,*t)):
        raise ValueError('finite float32 domain required')
    q=t[4:]; r=p[4:]
    product=[f(q[i]*p[i]) for i in range(4)]
    dot=f(product[0]+f(product[1]+product[2]))
    scale=f(f(q[3]*q[3])-.5)
    cross=[f(f(q[(i+1)%3]*p[(i+2)%3])-f(p[(i+1)%3]*q[(i+2)%3])) for i in range(3)]
    cross.append(f(f(q[3]*p[3])-f(p[3]*q[3])))
    position=[]
    for i in range(4):
        value=f(f(f(dot*q[i])+f(cross[i]*q[3]))+f(scale*p[i]))
        position.append(f(f(value*(2.0 if i<3 else 0.0))+t[i]))
    # Match SIMD grouping: ((qw*r + x-term) + y-term), then z-term + sum.
    xterms=(r[3],-r[2],r[1],-r[0])
    yterms=(r[2],r[3],-r[0],-r[1])
    zterms=(-r[1],r[0],r[3],-r[2])
    rotation=[f(f(q[2]*zterms[i])+f(f(f(q[3]*r[i])+f(q[0]*xterms[i]))+f(q[1]*yterms[i]))) for i in range(4)]
    return struct.pack('<8f',*position,*rotation)
