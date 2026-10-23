"""Detached ownership rules for vector/scalar action-source reads.

Evidence: INPUT_UPDATE_ORDER.md, Two ownership gates before source evaluation.
These snapshots do not acquire locks or pin native object lifetimes.
"""


def priority_blocks(owners_high_to_low, adapter):
    """First nonzero of exactly seven priority entries owns the query."""
    owners = tuple(owners_high_to_low)
    if len(owners) != 7:
        raise ValueError('seven priority entries required')
    for value in (*owners, adapter):
        if type(value) is not int or not 0 <= value < 2**64:
            raise ValueError('uint64 identity required')
    for owner in owners:
        if owner:
            return owner != adapter
    return False


def cache_owner_blocks(owners):
    """The final cache owner blocks a raw read whenever it is nonzero.

    Unlike priority_blocks, no comparison with the requesting adapter occurs.
    """
    owners = tuple(owners)
    if len(owners) > 65535:
        raise ValueError('uint16 owner count required')
    for value in owners:
        if type(value) is not int or not 0 <= value < 2**64:
            raise ValueError('uint64 identity required')
    return bool(owners and owners[-1])
