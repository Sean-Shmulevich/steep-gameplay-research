"""Callback adapter for the canonical vector_action_source implementation.

The separate vector/scalar gate keywords are a convenience API. Native evidence
and the selection rules are maintained in engine.vector_action_source.
"""
from .vector_action_source import select_vector_source as _select


def select_vector_source(mode, lane, *, vector_blocked, scalar_blocked,
                         read_vector, read_scalar):
    """Return raw 16-byte input before processor response/publication.

    Gate callbacks must represent low-byte boolean results. Missing source
    configuration remains outside this helper: the original evaluator skips
    updating its prior output when configuration is missing.
    """
    def blocked(family, index):
        return (vector_blocked if family == 'vector' else scalar_blocked)(index)
    return _select(mode, lane, blocked, read_vector, read_scalar)
