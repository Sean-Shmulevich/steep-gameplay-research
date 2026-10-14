"""Recovered runtime class-0 identity lookup; authored map population is open.

Rows contain a 16-byte key and uint32 value. This is not a clip UID resolver.
Native map storage and allocation are replaced with explicit caller snapshots.
"""
import struct


def _key(key):
    if not isinstance(key, bytes) or len(key) != 16:
        raise ValueError('identity must be exactly 16 bytes')
    return key


def _uint(value):
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('expected uint32')
    return value


def identity_bucket(identity, capacity):
    """Recovered word-wise multiply/XOR, low31 fold, then triangular probing seed."""
    _key(identity)
    if type(capacity) is not int or capacity <= 0 or capacity & (capacity - 1):
        raise ValueError('capacity must be a positive power of two')
    h = 0x811c9dc5
    for word in struct.unpack('<QQ', identity):
        h = ((h * 0x1000193) ^ word) & 0xffffffffffffffff
    h &= 0x7fffffff
    quotient, remainder = divmod(h, 127773)
    mixed = remainder * 16807 - quotient * 2836
    if mixed < 0:
        mixed += 0x7fffffff
    return mixed & (capacity - 1)


def lookup_identity(identity, rows, *, empty_key, deleted_key,
                    tombstones_enabled=False, counter_a=1, counter_b=0,
                    initial_value=0xffffffff):
    """Return (found, output_value), preserving zero-identity output retention.

    Counter names retain unresolved native semantics. Equality skips the search;
    counter_a > 0 enables the deleted-key check when tombstones_enabled is true.
    Invalid/full snapshots raise instead of reproducing an unbounded native loop.
    """
    identity, empty_key, deleted_key = map(_key, (identity, empty_key, deleted_key))
    _uint(initial_value)
    for counter in (counter_a, counter_b):
        if type(counter) is not int or not 0 <= counter < 1 << 64:
            raise ValueError('expected uint64 counter')
    if type(tombstones_enabled) is not bool:
        raise ValueError('tombstones_enabled must be bool')
    if identity == bytes(16):
        return False, initial_value
    if counter_a == counter_b:
        return False, 0
    rows = tuple(rows)
    index = identity_bucket(identity, len(rows))
    for key, value in rows:
        _key(key)
        _uint(value)
    for step in range(1, len(rows) + 1):
        key, value = rows[index]
        if key == empty_key:
            return False, 0
        if not (tombstones_enabled and counter_a > 0 and key == deleted_key):
            if key == identity:
                return True, value
        index = (index + step) & (len(rows) - 1)
    raise ValueError('identity map has no reachable match or empty slot')


def compile_identity(identity, rows, *, dependencies=None, **lookup_options):
    """Model class-0 compile result and successful unique dependency insertion.

    The compiler seeds the lookup output with UINT32_MAX and replaces the
    variant payload even on failure. Returned error must be checked before use.
    Variant allocation/type metadata are outside this portable boundary.
    """
    if 'initial_value' in lookup_options:
        raise ValueError('compiler fixes the initial value to UINT32_MAX')
    found, value = lookup_identity(identity, rows, **lookup_options)
    if found and dependencies is not None and value not in dependencies:
        dependencies.append(value)
    return {'binding_class': 0, 'value': value, 'error': 0 if found else 1}
