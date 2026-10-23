"""Local action reset and stable three-group refresh traversal.

Evidence under docs/reconstruction/: ACTION_PUBLICATION_FOLLOWUP.md,
"The reset reaches the sampled vector"; ACTION_RESET_CALLBACK.md; and
INPUT_TO_ACTION_ROUTE.md, "Runnable local refresh reconstruction". These are independent
adapters, not a scheduler, a tagged-map enumerator or a synchronization layer.
Map order and concrete source evaluators must be supplied by the caller.
"""
from collections.abc import Callable, Sequence


def reset_action(snapshot: bytes, *, owner_suppressed: bool,
                 evaluate: Callable[[bytes], bytes]) -> bytes:
    """Clear sample/direction/magnitude, preserve status, then optionally evaluate.

    The snapshot covers at least the sample fields through offset 0x83. Raw
    input at 0x50, status at 0x30 and all other bytes are preserved by reset.
    owner_suppressed is the caller's resolved optional-owner gate. The evaluator
    gets the cleared snapshot and must return the same-size bytes object.
    Exceptions propagate; there is no invented neutral-input fallback.

    Native code mutates the action in place. This adapter returns a copy and
    preserves arbitrary float bit patterns outside the cleared fields.
    """
    if not isinstance(snapshot, bytes) or len(snapshot) < 0x84:
        raise ValueError('action snapshot must be bytes covering offset 0x83')
    if type(owner_suppressed) is not bool:
        raise ValueError('owner_suppressed must be a resolved boolean gate')
    if not callable(evaluate):
        raise TypeError('an explicit action evaluator is required')
    cleared = snapshot[:0x60] + bytes(0x24) + snapshot[0x84:]
    if owner_suppressed:
        return cleared
    result = evaluate(cleared)
    if not isinstance(result, bytes) or len(result) != len(snapshot):
        raise ValueError('action evaluator must return same-size bytes')
    return result


def refresh_groups(groups: Sequence[Sequence], *, reset_binding: Callable,
                   blocker_enabled: Callable) -> None:
    """Refresh exactly three stable groups; blockers stop only their own group.

    Groups are visited forward and bindings backward. The blocker is queried
    AFTER reset/evaluation, so effects of that callback can change the gate.
    Binding identity is retained; duplicates are not removed. The caller owns
    map enumeration, context activity, preamble and manager accounting.
    Structural mutation during traversal is outside this adapter's contract.
    """
    if len(groups) != 3:
        raise ValueError('refresh requires exactly three groups')
    for group in groups:
        for binding in reversed(group):
            reset_binding(binding)
            if blocker_enabled(binding):
                break
