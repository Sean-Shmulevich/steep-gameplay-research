"""World-scaled pending producer; original reference sources remain immutable."""
from reference.central_impulse import f32


def queue_world_scaled_pending(pending, contribution, world_interval):
    """RVA 0x1373c10 arithmetic after entity/runtime/world presence guards.

    Evidence: CENTRAL_IMPULSE.md, World-interval-scaled callback accumulation.
    Inputs are finite four-lane vectors. No body mutation, ownership, locking,
    native pointer guards or substep scheduling is supplied by this kernel.
    """
    if len(pending) != 4 or len(contribution) != 4:
        raise ValueError('four lanes required')
    pending = tuple(f32(v) for v in pending)
    contribution = tuple(f32(v) for v in contribution)
    scale = f32(f32(world_interval) * f32(30.0))
    return tuple(f32(f32(scale * v) + p) for p,v in zip(pending,contribution))
