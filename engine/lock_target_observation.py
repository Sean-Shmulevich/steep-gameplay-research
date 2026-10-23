"""Bounded observation of build-specific encoded call-target slots.

Evidence: REQUEST_COMMAND_LIFECYCLE.md, Encoded lock-wrapper targets.
This decodes targets only. It never calls them or infers synchronization semantics.
Returned addresses are session-private. Caller verifies build and relocation;
the instruction fixture validates only the inspected preferred image base.
"""

# Names describe existing caller use, not established Windows API identities.
LOCK_TARGET_PROFILES = {
    'enter_helper': (0x3D9BC2D, 0x796E0B07),
    'leave_helper': (0x3C7A1B2, 0x7B907D10),
}

INITIALIZE_TARGET_PROFILE = (0x37EDE4A, 0x5A0D734C)


def decode_target(encoded, addend):
    """Recovered modular uint64 addition; does not validate a callable target."""
    if any(type(v) is not int or not 0 <= v < 2**64 for v in (encoded, addend)):
        raise ValueError('uint64 encoded value and addend required')
    return (encoded + addend) & (2**64 - 1)


def observe_lock_targets(read, *, image_base, image_size, include_initializer=False):
    """Read enter/leave twice, optionally initialization: four or six reads.

    Requests at most 32 bytes by default or 48 with initialization included.
    No retry or writes. API names must still be resolved for the current process.

    Stable equality is diagnostic, not an atomic snapshot or lifetime guarantee.
    A target in the usual lower 48-bit user range is not necessarily mapped,
    executable, an import, or a lock API. Resolve modules/exports separately.
    """
    if type(include_initializer) is not bool:
        raise ValueError('boolean initializer selection required')
    profiles = dict(LOCK_TARGET_PROFILES)
    if include_initializer:
        profiles['initialize_helper'] = INITIALIZE_TARGET_PROFILE
    if (type(image_base) is not int or type(image_size) is not int
            or not 0 < image_base < 2**64 or image_size <= 0
            or image_base + image_size > 2**64
            or any(offset+8 > image_size for offset, _ in profiles.values())):
        raise ValueError('image range must contain selected encoded slots')
    reads = 0
    class Refused(Exception):
        pass
    def sample():
        nonlocal reads
        values = {}
        for name, (offset, addend) in profiles.items():
            reads += 1
            value = read(image_base+offset, 8)
            if not isinstance(value, bytes) or len(value) != 8:
                raise Refused('short_read')
            values[name] = int.from_bytes(value, 'little')
        return values
    result = {}
    try:
        first, second = sample(), sample()
        if first != second:
            result['status'] = 'unstable'
        else:
            result['status'] = 'observed'
            result['targets'] = {
                name: decode_target(value, profiles[name][1])
                for name, value in first.items()
            }
            result['all_targets_in_lower_48bit_user_range'] = all(
                0 < value < 2**47 for value in result['targets'].values())
    except Refused as exc:
        result['status'] = str(exc)
    except OSError:
        result['status'] = 'read_failed'
    return dict(result, reads=reads, requested_bytes=reads*8,
                atomic_snapshot=False, api_identity_proved=False,
                native_lock_semantics_proved=False)
