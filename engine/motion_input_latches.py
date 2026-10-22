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


@dataclass(frozen=True)
class BaselinePublication:
    primary: bytes
    secondary: bytes
    smoothed: bytes
    copied_word_bits: int


def refresh_input_baselines(primary: bytes, secondary: bytes, current: bytes,
                            smoothed: bytes, alpha: float,
                            copied_word_bits: int) -> BaselinePublication:
    """Selected branch only; caller owns cadence and actor-predicate selection.

    Baselines copy ingestion vectors verbatim. Smoothing uses a separate current
    vector; it must not silently be replaced with primary. Alpha is not clamped.
    """
    for value in (primary, secondary, current, smoothed):
        if not isinstance(value, bytes) or len(value) != 16:
            raise ValueError('vectors must be 16 immutable bytes')
    if type(copied_word_bits) is not int or not 0 <= copied_word_bits <= 0xffffffff:
        raise ValueError('copied word must be unsigned 32-bit bits')
    alpha = _f32(alpha)
    complement = _f32(1.0-alpha)
    result = [_f32(_f32(complement*a)+_f32(alpha*b))
              for a,b in zip(struct.unpack('<4f',smoothed),struct.unpack('<4f',current))]
    return BaselinePublication(primary, secondary, struct.pack('<4f',*result), copied_word_bits)


@dataclass(frozen=True)
class ResetPrefixResult:
    latches: InputLatches
    preserved_combined_byte: int


def reset_input_latch_prefix(count: int, threshold: int,
                             combined_byte: int) -> ResetPrefixResult:
    """Inspected reset prefix; stored combined byte is deliberately preserved."""
    for value in (count, threshold):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError('count and threshold must be unsigned 32-bit integers')
    if type(combined_byte) is not int or not 0 <= combined_byte <= 255:
        raise ValueError('combined byte must be unsigned byte')
    return ResetPrefixResult(InputLatches(count <= threshold, False), combined_byte)
