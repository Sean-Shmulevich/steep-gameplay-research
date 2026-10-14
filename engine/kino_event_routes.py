"""KinoComponent's two constructor-installed event-route groups.

Callers resolve the component token and supply its owning object's mode byte.
This module does not perform native type lookup or infer a player association.
"""


def kino_event_slots(owner_mode_byte):
    """Return the unconditional time slot and selected secondary slot."""
    if type(owner_mode_byte) is not int or not 0 <= owner_mode_byte <= 255:
        raise ValueError('owner mode must be uint8')
    return (16, 23 if owner_mode_byte & 7 == 1 else 22)


def kino_removal_slots():
    """Cleanup candidates for both groups; secondary conditional before fallback.

    Combining the groups in this order is an adapter choice. Each secondary
    group removes both candidates without reevaluating its predicate.
    """
    return (16, 23, 22)
