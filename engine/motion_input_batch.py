"""Authored batch interface around the recovered motion-ingestion prefix.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Live input changes inside
BeforeSimulation. The once-per-batch composition is supported by one captured
moving-player state, not all modes. Callers resolve activation gates and supply
four independent action reads; no keyboard mapping or body actuation is invented.
"""
from dataclasses import dataclass
import math
from .motion_input_ingestion import IngestedMotion, action_read_sequence, ingest_motion_prefix


@dataclass(frozen=True)
class MotionInputBatch:
    motion: IngestedMotion
    # Immutable copies of scheduler elapsed/derivative intervals.
    steps: tuple[tuple[float, float], ...]
    action_ids: tuple[int, ...]
    refreshed: bool

    def execute(self, update):
        """Call update(ordinal, elapsed, derivative, motion) in plan order.

        No action re-read occurs here. Exceptions propagate and previously run
        callbacks are not rolled back. This does not execute the original solver.
        """
        if not callable(update):
            raise ValueError('a physics update callback is required')
        for ordinal, (elapsed, derivative) in enumerate(self.steps):
            update(ordinal, elapsed, derivative, self.motion)


def prepare_motion_input_batch(previous, steps, *, ingestion_enabled,
                               read_action, alternate_enabled, actor_predicate,
                               flip_x, alpha):
    """Prepare one BeforeSimulation result for a supplied physics step plan.

    Gate selection, actor ownership and profile lifetime belong to the caller.
    Suppressed ingestion retains previous state without action reads. A zero-step
    plan still performs eligible ingestion: the caller has requested the outer
    callback independently of whether physics work follows. That empty-plan
    behavior is an interface choice, not a live observation.
    """
    if not isinstance(previous, IngestedMotion):
        raise ValueError('previous ingested state required')
    for flag in (ingestion_enabled, alternate_enabled, actor_predicate, flip_x):
        if type(flag) is not bool:
            raise ValueError('explicit resolved boolean gates required')
    if not callable(read_action):
        raise ValueError('action reader required')
    plan = []
    for step in steps:
        elapsed, derivative = step['elapsed_dt'], step['derivative_dt']
        if any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0
               for x in (elapsed, derivative)):
            raise ValueError('positive finite step intervals required')
        plan.append((float(elapsed), float(derivative)))
    if not ingestion_enabled:
        return MotionInputBatch(previous, tuple(plan), (), False)
    ids = action_read_sequence(alternate_enabled, actor_predicate)
    # Do not coalesce repeated IDs: the recovered routine reads each separately.
    reads = tuple(read_action(action) for action in ids)
    motion = ingest_motion_prefix(reads, flip_x=flip_x,
        counts=(previous.primary_count, previous.secondary_count),
        smoothed=(previous.smoothed_primary, previous.smoothed_secondary), alpha=alpha)
    return MotionInputBatch(motion, tuple(plan), ids, True)
