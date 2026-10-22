"""Local input-change latch arithmetic, not action ingestion or actuation.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, 'Input-change latch consumer'.
External setting/action eligibility and baseline production remain inputs.
"""
from dataclasses import dataclass
import math
import struct


def _f32(value):
    try:
        return struct.unpack('<f', struct.pack('<f', value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


@dataclass(frozen=True)
class InputLatches:
    first: bool
    second: bool

    @property
    def combined(self):
        return self.first or self.second


def update_input_latches(state: InputLatches, *, current_xy, baseline_xy,
                         current_secondary_y, baseline_secondary_y,
                         first_count: int, second_count: int, threshold,
                         setting_gate: bool, action_gate: bool,
                         secondary_suppressed: bool) -> InputLatches:
    """Preserve already-set latches and apply the observed float32 tests.

    Counts are unsigned ingestion histories. No elapsed-time conversion, reset,
    profile lookup, helper side effects or update cadence is supplied here.
    """
    for count in (first_count, second_count):
        if type(count) is not int or not 0 <= count <= 0xffffffff:
            raise ValueError('counts must be unsigned 32-bit integers')
    if len(current_xy) != 2 or len(baseline_xy) != 2:
        raise ValueError('first channel needs XY pairs')
    threshold = _f32(threshold)
    first = state.first
    if not first:
        delta = [_f32(_f32(a)-_f32(b)) for a,b in zip(baseline_xy,current_xy)]
        distance = _f32(_f32(delta[0]*delta[0])+_f32(delta[1]*delta[1]))
        # Original JA is false for unordered comparisons.
        retain_clear = ((setting_gate or action_gate) and
                        not (distance > threshold) and
                        (first_count > 3 or action_gate))
        first = not retain_clear
    second = state.second
    if not second and not secondary_suppressed:
        delta = _f32(_f32(baseline_secondary_y)-_f32(current_secondary_y))
        second = _f32(delta*delta) > threshold or second_count <= 3
    return InputLatches(bool(first), bool(second))
