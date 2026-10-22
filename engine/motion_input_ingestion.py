"""Recovered ingestion prefix, not device polling or a scheduling policy.

Evidence: docs/reconstruction/MOTION_MEMBERSHIP_OBSERVATION.md,
"Ingestion read sequence and both smoothing writers". Action payloads are four
separately supplied reads in execution order. No freshness guarantee is implied.
"""
from dataclasses import dataclass
import struct
from .motion_input_latches import refresh_input_baselines


def action_read_sequence(alternate_enabled: bool, actor_predicate: bool) -> tuple:
    """Action IDs requested in order; actor predicate is queried only if enabled."""
    return (0xd9 if alternate_enabled and actor_predicate else 0x76, 0x77, 0x76, 0x77)


def _vector(value: bytes, flip_x: bool) -> bytes:
    if not isinstance(value, bytes) or len(value) != 16:
        raise ValueError('action vectors must be 16 immutable bytes')
    words = list(struct.unpack('<4I', value))
    if flip_x:
        words[0] ^= 0x80000000
    return struct.pack('<4I', *words)


def _count(value: bytes, previous: int) -> int:
    if type(previous) is not int or not 0 <= previous <= 0xffffffff:
        raise ValueError('history counter must be uint32')
    x, y = struct.unpack('<2I', value[:8])
    # SSE unordered comparisons count NaNs as nonzero; +/-zero both reset.
    return (previous + 1) & 0xffffffff if (x & 0x7fffffff) or (y & 0x7fffffff) else 0


@dataclass(frozen=True)
class IngestedMotion:
    primary: bytes
    secondary: bytes
    current_primary: bytes
    current_secondary: bytes
    primary_count: int
    secondary_count: int
    smoothed_primary: bytes
    smoothed_secondary: bytes
    reset_byte: int = 0


def ingest_motion_prefix(reads: tuple, *, flip_x: bool, counts: tuple,
                         smoothed: tuple, alpha: float) -> IngestedMotion:
    """Through second smoothing store; excludes helper and actor-edge tail.

    Caller supplies already-resolved action reads and profile coefficient.
    Ingestion call cadence, profile lifetime and action-view ownership are open.
    """
    if len(reads) != 4 or len(counts) != 2 or len(smoothed) != 2:
        raise ValueError('expected four reads, two counters and two smoothed vectors')
    primary, secondary, current_primary, current_secondary = [_vector(v, flip_x) for v in reads]
    first = _count(primary, counts[0]); second = _count(secondary, counts[1])
    smooth = lambda current, old: refresh_input_baselines(primary, secondary, current, old, alpha, 0).smoothed
    return IngestedMotion(primary, secondary, current_primary, current_secondary,
                          first, second, smooth(current_primary, smoothed[0]),
                          smooth(current_secondary, smoothed[1]))
