"""Read-only UI command-owner qualification for a caller-verified build.

See ANIMATION_CONTEXT_RETIREMENT.md, named owner correction. Profiles contain
relocated addresses, never saved heap pointers. Equal samples are not a lifetime
pin, an atomic snapshot, proof of registration, or permission to call methods.
"""
import struct


def observe_command_owner(read, *, owner_global, participant_global,
                          embedded_offset, participant_table, participant_methods,
                          owner_profiles, image_range, code_range):
    """Profiles map owner table addresses to name and three lifecycle methods.

    Methods are ordered destructor, registration, removal, at slots 0/0x90/0xc8.
    Uses at most 16 reads and 144 bytes. Does not write or execute engine code.
    """
    def address(value):
        return type(value) is int and 0 < value < 2**64
    lo, hi = image_range
    clo, chi = code_range
    if not all(address(x) for x in (lo, hi, clo, chi)) or not lo <= clo < chi <= hi:
        raise ValueError('ordered image and contained code ranges required')
    if type(embedded_offset) is not int or not 0 < embedded_offset < 2**32:
        raise ValueError('positive embedded offset required')
    def within(a, n):
        return address(a) and lo <= a <= hi-n
    if not all(within(a, 8) for a in (owner_global, participant_global)):
        raise ValueError('globals must belong to image')
    if not within(participant_table, 16):
        raise ValueError('participant table must belong to image')
    def methods_valid(methods, n):
        return len(methods) == n and all(address(x) and clo <= x < chi for x in methods)
    if not methods_valid(participant_methods, 2) or not owner_profiles:
        raise ValueError('qualified method profiles required')
    for table, profile in owner_profiles.items():
        if (not within(table, 0xd0) or not isinstance(profile['name'], str)
                or not profile['name'] or not methods_valid(profile['methods'], 3)):
            raise ValueError('invalid owner profile')
    reads = total = 0
    class Refused(Exception):
        pass
    def get(a, n):
        nonlocal reads, total
        if not address(a) or a+n > 2**64:
            raise Refused('invalid_address')
        reads += 1
        total += n
        value = read(a, n)
        if not isinstance(value, bytes) or len(value) != n:
            raise Refused('short_read')
        return struct.unpack('<'+'Q'*(n//8), value)
    def q(a):
        return get(a, 8)[0]
    def sample():
        owner, participant = q(owner_global), q(participant_global)
        if not owner or not participant:
            raise Refused('owner_unavailable')
        if owner + embedded_offset >= 2**64 or owner + embedded_offset != participant:
            raise Refused('owner_link_mismatch')
        if q(participant) != participant_table:
            raise Refused('participant_table_mismatch')
        if get(participant_table, 16) != tuple(participant_methods):
            raise Refused('participant_methods_mismatch')
        table = q(owner)
        if table not in owner_profiles:
            raise Refused('unknown_owner_table')
        profile = owner_profiles[table]
        methods = tuple(q(table+slot) for slot in (0, 0x90, 0xc8))
        if methods != tuple(profile['methods']):
            raise Refused('owner_methods_mismatch')
        return dict(owner=owner, participant=participant, owner_table=table,
                    owner_type=profile['name'], lifecycle_methods=list(methods))
    try:
        first, second = sample(), sample()
        result = dict(status='observed', identity=first) if first == second else dict(status='unstable')
    except Refused as exc:
        result = dict(status=str(exc))
    except (OSError, ValueError, struct.error):
        result = dict(status='invalid')
    return dict(result, reads=reads, bytes=total, atomic_snapshot=False,
                lifetime_pinned=False, registration_proved=False, execution_proved=False)
