"""Concrete registered selection-mask value services for the inspected build.

Evidence: CENTRAL_IMPULSE.md, Concrete animation service implementations.
No heap ownership or reference counting; owner arguments are unused by these leaves.
"""


def acquire_selection_mask(blend_mask_word=None):
    """None means absent blend-mask object; otherwise supplied word at its +0x40."""
    return 65535 if blend_mask_word is None else int(blend_mask_word) & 65535


def copy_selection_mask(owner, value):
    return int(value) & 0xffffffffffffffff


def release_selection_mask(owner, value):
    return None


def intersect_selection_masks(a, b):
    return (int(a) & int(b)) & 65535


def union_selection_masks(a, b):
    return (int(a) | int(b)) & 65535


def is_active_selection_mask(value):
    return bool(int(value) & 65535)
