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


def dispatch_contact_pair(handlers, first_resources, second_resources,
                          first_index, second_index, descriptor, records, *,
                          cache, recycled, key_width, process_groups, clear_pair):
    """Recovered generation-to-cache handoff with supplied downstream services.

    Resources supply raw ``kind`` values. The selected callable receives
    (descriptor, records, 500). Services own cache mutation and payload lifetime.
    Return count is an authored diagnostic; native wrappers return no count.
    """
    if key_width not in (16, 32):
        raise ValueError('Explicit 16 or 32 bit grouping key required')
    if len(records) < 500 * 48:
        raise ValueError('Backing storage for 500 records required')
    if any(type(i) is not int or not 0 <= i <= 0xffff
           for i in (first_index, second_index)):
        raise ValueError('Pair indices must be uint16')
    handler = select_contact_handler(handlers, first_resources[first_index]['kind'],
                                     second_resources[second_index]['kind'])
    if not callable(handler):
        raise ValueError('Selected handler must be supplied; no fallback')
    count = handler(descriptor, records, 500)
    if type(count) is not int or not 0 <= count <= 500:
        raise ValueError('Handler returned a count outside backing storage')
    if count:
        process_groups(cache, records, count, first_index, second_index,
                       recycled, key_width)
    else:
        clear_pair(cache, first_index, second_index, recycled)
    return count
