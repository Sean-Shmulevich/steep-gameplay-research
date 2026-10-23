"""Recovered metadata registration and default selection, not region ownership.

Evidence: RESOURCE_RETIREMENT.md, Metadata registration and default selection.
Caller retains registry, records, observers and callback modules.
"""


def register_metadata(registry, record, *, lock, unlock, notify_object, notify_function):
    """Register an unassigned record in the first free entry among 127 slots.

    record.index is a byte, 255 means unassigned. Any other existing index returns
    success without checking this registry or notifying. Entries use None for
    native null. Observers contain object_style, target and context. Notifications
    occur after unlocking, with event zero. Length is re-read after callbacks;
    callbacks must retain storage and preserve a reachable traversal endpoint.
    Normal-return serial model only, with no invented rollback or ownership pin.
    """
    if record['index'] != 255:
        return True
    lock(registry)
    inserted = False
    for index in range(127):
        if registry['entries'][index] is None:
            record['index'] = index
            registry['entries'][index] = record
            inserted = True
            break
    unlock(registry)
    if inserted:
        index = 0
        while index != len(registry['observers']):
            observer = registry['observers'][index]
            if observer['object_style']:
                notify_object(observer['target'], 0, record)
            else:
                notify_function(0, record, observer['context'], observer['target'])
            index += 1
    return inserted


def select_default_metadata(registry, record, **services):
    """Register then copy the current record index even when registration fails."""
    result = register_metadata(registry, record, **services)
    registry['default'] = record['index']
    return result
