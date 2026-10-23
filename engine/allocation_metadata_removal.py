"""Recovered metadata removal and observer dispatch.

Evidence: RESOURCE_RETIREMENT.md, Metadata removal and notifications.
Region retirement, callback lifetime and allocator release remain external.
"""


def notify_metadata_observers(observers, event, record, *, notify_object, notify_function):
    """Traverse a retained list, re-reading length, OR-ing uint32 callback results.

    The caller selects the event's observer collection. Callbacks may append;
    they must not invalidate storage or shrink the endpoint behind traversal.
    """
    combined = 0
    index = 0
    while index != len(observers):
        observer = observers[index]
        if observer['object_style']:
            result = notify_object(observer['target'], event, record)
        else:
            result = notify_function(event, record, observer['context'], observer['target'])
        combined |= result & 0xffffffff
        index += 1
    return combined


def unregister_metadata(registry, record, *, lock, unlock, notify_object, notify_function):
    """Capture index before lock, clear that entry, notify, then set index to 255.

    Scope requires index0..126 and externally retained storage. The native routine
    does not check bounds or verify the table entry equals record; this model does
    not supply that missing membership check. Default clears only on index match.
    Notifications use event0 after unlocking and before resetting record.index.
    Region tags are untouched. Callback failure has no synthetic cleanup path.
    """
    index = record['index']
    lock(registry)
    registry['entries'][index] = None
    if registry['default'] == index:
        registry['default'] = 255
    unlock(registry)
    result = notify_metadata_observers(registry['observers'], 0, record,
        notify_object=notify_object, notify_function=notify_function)
    record['index'] = 255
    return result
