"""Decision portion of the motion query guard, without native lock/services.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, 'State guard and deferred work'.
Numeric state labels remain unidentified. This does not execute state changes.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardDecision:
    return_value: bool
    output_byte: int


def evaluate_guard(bypass_count: int, parent_state: int, child_state: int,
                   initial_output: int = 0) -> GuardDecision:
    """Apply the local predicate; preserve output unless the branch sets it.

    Lock ownership, query-depth bookkeeping and pending-service execution are
    the caller's responsibility. An output byte of one is not a freshness tag.
    """
    for value in (bypass_count, parent_state, child_state):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError('state/count fields must be unsigned 32-bit integers')
    if type(initial_output) is not int or not 0 <= initial_output <= 255:
        raise ValueError('output must be an unsigned byte')
    blocks = bypass_count == 0 and (
        (parent_state == 3 and child_state == 2) or
        (parent_state == 0 and child_state in (0, 3, 4)))
    return GuardDecision(not blocks, 1 if blocks else initial_output)
