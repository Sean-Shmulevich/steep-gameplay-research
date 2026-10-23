"""Recovered cache readiness rules; device acquisition and query remain external.

Evidence: INPUT_UPDATE_ORDER.md, Cache-type readiness callbacks.
Names describe our interfaces, not recovered original class names.
"""


def _uint(value, bits):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(f'uint{bits} required')
    return value


def queried_cache_ready(slot, query):
    """Query a uint32 slot with a zeroed 16-byte scratch buffer; zero means ready.

    Buffer writes are discarded, as in the original callback. Query is invoked
    once and must return a uint32 status. The query implementation is unresolved.
    """
    result = query(_uint(slot, 32), bytearray(16))
    return _uint(result, 32) == 0


def linked_cache_ready(override_byte, device_identity):
    """Nonzero uint8 override bypasses the uint64 device-identity check."""
    if _uint(override_byte, 8):
        return True
    return _uint(device_identity, 64) != 0


def extended_cache_ready(device_identity):
    """Readiness of the extended cache is just a non-null uint64 identity."""
    return _uint(device_identity, 64) != 0
