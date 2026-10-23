"""Convenience wrappers around canonical vector_action_source ownership rules.

Snapshots do not acquire locks or pin native object lifetimes. No independent
copy of the selection/masking rules is maintained here.
"""
from .vector_action_source import priority_blocks as _priority_blocks, cached_value


def priority_blocks(owners_high_to_low, adapter):
    """First nonzero of seven entries owns the query; adapter must be nonzero."""
    return _priority_blocks(adapter, tuple(owners_high_to_low))


def cache_owner_blocks(owners):
    """Any nonzero final cache owner blocks, regardless of requester identity."""
    return cached_value(b'\x01\x00\x00\x00', tuple(owners)) == bytes(4)
