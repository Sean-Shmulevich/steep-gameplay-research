"""Recovered saved-name preference before fallback cache selection.

Evidence: INPUT_UPDATE_ORDER.md, Saved-name restoration before fallback.
Names are explicit UTF-16LE storage, not normalized Python display strings.
"""


def _name(storage):
    if not isinstance(storage, bytes) or len(storage) % 2:
        raise ValueError('even-length UTF-16LE bytes required')
    for offset in range(0, len(storage), 2):
        if storage[offset:offset+2] == b'\0\0':
            return storage[:offset]
    raise ValueError('NUL-terminated UTF-16LE storage required')


def preferred_input_cache(saved_name, record_names, ready):
    """Return first same-name index whose readiness callback has nonzero low byte.

    Empty saved name bypasses record reads and callbacks. Matching is exact
    uint16-unit equality through NUL, case-sensitive, without normalization.
    ready(index) must return a uint32 result; only its low byte is tested.
    No index setter, mutation, native query or scheduler interaction occurs.
    Names/count must remain stable during this independent decision.
    """
    saved = _name(saved_name)
    if not saved:
        return None
    records = tuple(record_names)
    if len(records) > 65535:
        raise ValueError('uint16 record count required')
    for index, storage in enumerate(records):
        if _name(storage) == saved:
            result = ready(index)
            if type(result) is not int or not 0 <= result < 1 << 32:
                raise ValueError('uint32 readiness result required')
            if result & 255:
                return index
    return None
