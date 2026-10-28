"""Pair-handler lookup; LINK_SOLVER.md, Resource-pair dispatch lookup.

Handler identities and ownership are supplied. No native pointer is reused.
"""


def select_contact_handler(handlers, first_kind, second_kind):
    """Resolve two raw uint16 resource kinds in an 8 by 8 handler table.

    Bit15 is excluded from lookup. Reject out-of-table kinds rather than emulate
    an unchecked native read. None is a valid empty slot and has no fallback.
    """
    if len(handlers) != 64:
        raise ValueError('Complete 64-slot handler table required')
    if any(type(kind) is not int or not 0 <= kind <= 0xffff
           for kind in (first_kind, second_kind)):
        raise ValueError('Raw uint16 resource kinds required')
    first, second = first_kind & 0x7fff, second_kind & 0x7fff
    if first >= 8 or second >= 8:
        raise ValueError('Masked resource kind outside handler table')
    return handlers[8 * first + second]
