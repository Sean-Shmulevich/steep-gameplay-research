"""Recovered cache publication copy and full reset over explicit raw snapshots.

Evidence: INPUT_UPDATE_ORDER.md, Selected-device publication into the root.
No device polling, scheduler, timestamp production or callback execution.
"""
from engine.action_cache_exchange import CACHE_SPAN, EXCHANGED_RANGES


def _snapshot(value):
    if not isinstance(value, bytes) or len(value) != CACHE_SPAN:
        raise ValueError('exact 0x818-byte snapshot required')
    return value


def publish_selected_cache(root, selected):
    """Return root with prior buttons saved and selected channels copied.

    Detached stable snapshots; partially overlapping native objects are excluded.
    Identical root/selected input is allowed. Timestamps and derived buttons are
    unchanged here; the original invokes separate helpers after this copy.
    """
    root, selected = _snapshot(root), _snapshot(selected)
    result = bytearray(root)
    result[0x10:0x30] = root[0x30:0x50]
    for start, end in ((0x30, 0x50), (0x1f0, 0x210), (0x168, 0x1e8)):
        result[start:end] = selected[start:end]
    return bytes(result)


def reset_input_cache(snapshot):
    """Zero the full reset helper's fields, preserving unrelated bytes exactly."""
    result = bytearray(_snapshot(snapshot))
    for start, end in EXCHANGED_RANGES:
        result[start:end] = bytes(end - start)
    return bytes(result)
