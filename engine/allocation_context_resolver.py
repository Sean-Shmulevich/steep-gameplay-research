"""Recovered size-based context resolver; tables and capability query are supplied.

Evidence: REQUEST_COMMAND_LIFECYCLE.md, Size-based allocation context resolver.
Token meaning, actual heaps and ownership are not inferred from size selection.
"""
from .allocation_policy import _uint


def resolve_allocation_context(size, alignment, source, *, small_contexts,
                               special_contexts, query_alignment):
    """Return a supplied context token or zero using original unsigned arithmetic.

    small_contexts has 15 tokens for computed classes 8,12,...,64. Special
    candidates are keyed by exact request sizes 80,96,128. query_alignment(token)
    models the unresolved virtual method at slot +0x50. source is accepted for
    the caller interface but the inspected routine does not use its value.
    """
    _uint(size, 32, 'size'); _uint(alignment, 32, 'alignment')
    _uint(source, 64, 'source')
    if len(small_contexts) != 15:
        raise ValueError('small_contexts must contain 15 tokens')
    if alignment == 0xffffffff:
        alignment = 16 if size % 16 == 0 else 8 if size % 8 == 0 else 4
    if size <= 64:
        rounding = max(alignment, 4)
        rounded = ((max(size, alignment) - 1 + rounding) & 0xffffffff)
        rounded &= (~(rounding - 1)) & 0xffffffff
        rounded = max(rounded, 8)
        if rounded <= 64:
            return _uint(small_contexts[(rounded - 8) >> 2], 64, 'small context')
    if size in (80, 96, 128):
        candidate = _uint(special_contexts.get(size, 0), 64, 'special context')
        if candidate:
            supported = _uint(query_alignment(candidate), 32, 'query result')
            if supported >= alignment:
                return candidate
    return 0
