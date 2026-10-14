"""World event-list membership with recovered pointer-token semantics.

This serial adapter does not supply native locking or listener lifetime. Tokens
are caller-assigned uint64 values, not evidence of live game object identity.
"""

EVENT_SLOTS = 53
ANIMATION_TIME_SLOT = 16


def event_source_offset(slot):
    if type(slot) is not int or not 0 <= slot < EVENT_SLOTS:
        raise ValueError('event slot must be in 0..52')
    return 0x130 + 0x40 * slot


def _token(token):
    if type(token) is not int or not 0 <= token <= 0xffffffffffffffff:
        raise ValueError('listener token must be uint64')


def register_listener(entries, listener):
    """Append only if absent; return insertion as a portable diagnostic."""
    _token(listener)
    if listener in entries:
        return False
    entries.append(listener)
    return True


def remove_listener(entries, listener):
    """Find first match, fill its hole with the last entry, reduce count."""
    _token(listener)
    try:
        index = entries.index(listener)
    except ValueError:
        return False
    if index != len(entries) - 1:
        entries[index] = entries[-1]
    entries.pop()
    return True


class WorldEventRegistry:
    def __init__(self):
        self._entries = [[] for _ in range(EVENT_SLOTS)]

    def _entry(self, slot):
        event_source_offset(slot)
        return self._entries[slot]

    def register(self, slot, listener):
        return register_listener(self._entry(slot), listener)

    def remove(self, slot, listener):
        return remove_listener(self._entry(slot), listener)

    def snapshot(self, slot):
        """Owned list copy; no native atomic-snapshot guarantee."""
        return self._entry(slot).copy()
