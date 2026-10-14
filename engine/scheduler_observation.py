"""Read-only observation adapter for one inspected image's animation job layout.

The supplied readv transport must implement exact, bounded reads and its own
process identity checks/timeouts. No process access, pause or writes occur here.
Repeated equal samples do not prove atomicity, lifetime or safe stepping.
See docs/reconstruction/SCHEDULER_OBSERVATION.md.
"""
import struct
import time

IMAGE_SHA256 = '32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2'
JOBS = (
    ('UpdatePreActionGather', 0x1d8, 'callback'),
    ('UpdateCharacterActionSet', 0x2950, 'range'),
    ('SkelUpdateBeginAnimate', 0x57b0, 'range'),
    ('UpdateKino', 0x3938, 'callback'),
    ('AnimationUpdateTime', 0x3af0, 'range'),
    ('UpdateActionKinoStatesInteraction', 0x3050, 'range'),
    ('ActionGatherComponents', 0x2798, 'callback'),
)
TABLE_RVAS = {'callback': 0x1e89618, 'range': 0x1ec7f38}
FIELDS = ('executions', 'outstanding_dispatches', 'state', 'started',
          'requested', 'holds')


def _address(value, length=1):
    if type(value) is not int or not 0x10000 <= value < 0x800000000000:
        raise ValueError('expected a non-null user-space address')
    if value + length > 0x800000000000:
        raise ValueError('read exceeds user-space address range')
    return value


def observation_ranges(owner):
    """Seven job headers plus the separately established animation claim count."""
    _address(owner, 0x6000)
    return [(owner + offset, 0x64) for _, offset, _ in JOBS] + [
        (owner + 0x3af0 + 0x1a0, 4)]


def decode_sweep(blocks, image_base):
    _address(image_base, max(TABLE_RVAS.values()) + 8)
    if len(blocks) != 8 or any(type(b) is not bytes or len(b) != n
                              for b, n in zip(blocks, [0x64] * 7 + [4])):
        raise ValueError('expected seven exact headers and one claim count')
    result = {}
    for (name, _, kind), block in zip(JOBS, blocks):
        if struct.unpack_from('<Q', block)[0] != image_base + TABLE_RVAS[kind]:
            raise ValueError('job table mismatch: ' + name)
        row = dict(zip(FIELDS, struct.unpack_from('<6I', block, 0x4c)))
        row['state_name'] = {0: 'unscheduled', 1: 'scheduled', 2: 'done'}.get(
            row['state'], 'unknown')
        result[name] = row
    result['AnimationUpdateTime']['remaining_to_claim'] = struct.unpack('<i', blocks[7])[0]
    return result


def capture_pair(readv, owner, image_base, guards, *, clock=time.monotonic):
    """Two sequential sweeps, each bracketed by caller-supplied identity reads.

    guards is a nonempty sequence of (address, expected_bytes). Their meaning
    and adequacy remain the caller's responsibility. Limits bound work, not
    latency; the transport must enforce timeouts. Exceptions abort the capture.
    """
    ranges = observation_ranges(owner)
    _address(image_base, max(TABLE_RVAS.values()) + 8)
    guards = list(guards)
    if not 1 <= len(guards) <= 32:
        raise ValueError('provide 1..32 identity guards')
    for address, expected in guards:
        if type(expected) is not bytes or not 1 <= len(expected) <= 256:
            raise ValueError('guard must contain 1..256 expected bytes')
        _address(address, len(expected))
    guard_ranges = [(a, len(b)) for a, b in guards]
    expected = [b for _, b in guards]

    def read_exact(plan):
        values = list(readv(plan))
        if len(values) != len(plan) or any(type(b) is not bytes or len(b) != n
                                         for b, (_, n) in zip(values, plan)):
            raise ValueError('transport returned incomplete read')
        return values

    sweeps = []
    for _ in range(2):
        start = clock()
        if read_exact(guard_ranges) != expected:
            raise ValueError('identity guard changed before sweep')
        jobs = decode_sweep(read_exact(ranges), image_base)
        if read_exact(guard_ranges) != expected:
            raise ValueError('identity guard changed after sweep')
        sweeps.append(dict(read_start=start, read_end=clock(), jobs=jobs))
    changes = {}
    for name, _, _ in JOBS:
        a, b = (s['jobs'][name] for s in sweeps)
        changed = {key: [a[key], b[key]] for key in a if a[key] != b[key]}
        if changed:
            changes[name] = changed
    return dict(schema='scheduler-observation-v1', sweeps=sweeps, changes=changes,
                guards_matched=True, atomic_snapshot=False,
                safe_to_step_established=False, live_player_membership_established=False,
                limits=['Equal values can hide intervening updates or object reuse.',
                        'Request counters are not global frame identifiers.',
                        'Headers and claim count are read at different instants.',
                        'No submission exclusion or native thread context is established.'])
