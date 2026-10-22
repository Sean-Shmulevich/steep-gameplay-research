"""Snow batch preparation, under caller-owned stable registration snapshots.

Source: docs/reconstruction/SNOW_BATCH_DISPATCH.md. Tokens and immutable tuples
are authored representations. Native locks, allocation, lifetime and execution
are not supplied. This is distinct from the PreBeforeSimulation receiver array.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SnowRecord:
    tag: int
    actor: int | str


def gather_snow_records(actors, alternate):
    """Selector-zero gather: tag 0 first, then tag 2; preserve duplicates.

    Reject beyond packed capacity rather than emulate allocator failure or
    invalid native headers. Callers supply stable list/tuple snapshots.
    """
    if not isinstance(actors, (list, tuple)) or not isinstance(alternate, (list, tuple)):
        raise ValueError('Stable list/tuple snapshots required')
    if len(actors) + len(alternate) > 0x3fff:
        raise ValueError('Combined records exceed packed capacity')
    if any(type(x) not in (int, str) for x in (*actors, *alternate)):
        raise ValueError('Actor tokens must be integers or strings')
    return tuple(SnowRecord(0, x) for x in actors) + tuple(SnowRecord(2, x) for x in alternate)


def requested_claim_size(record_count):
    """Integer record-count partition, not a duration or substep count.

    Includes tag-two records, whose selected visitor is a no-op. Empty batches
    skip submission, although the local arithmetic still produces one.
    """
    if type(record_count) is not int or not 0 <= record_count <= 0xffff:
        raise ValueError('Record count must fit native unsigned 16-bit load')
    return max(record_count // 20, 1)
