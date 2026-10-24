"""Contact-volume profile accumulation and maximum selection.

Evidence: CENTRAL_IMPULSE.md, Contact-volume ownership of the base decay curve;
docs/systems/snow/contact-ownership/evidence.md, producer edge 5.
Keys are opaque uint64 identities within one supplied snapshot, not resource IDs.
Geometry admission, native container allocation/lifetime and profile lookup are
external. Do not retain these identities across native sessions.
"""
from reference.central_impulse import f32


def _key(value):
    if type(value) is not int or not 0 < value < (1 << 64):
        raise ValueError('Nonzero uint64 profile identity required')
    return value


def accumulate_profile_volumes(contributions):
    """Fold already-admitted cell helper returns in supplied execution order.

    The native map adds negative/zero returns too; positive-only total immersion
    is a separate accumulator. Start from the selected geometry update's empty
    map. No geometry eligibility or partial-update continuity is inferred.
    """
    volumes={}
    for entry in contributions:
        key=_key(entry['profile_key'])
        volumes[key]=f32(f32(entry['volume'])+volumes.get(key,0.0))
    return [dict(profile_key=key,volume=volumes[key]) for key in sorted(volumes)]


def select_volume_profile(entries):
    """Select maximum >= -1, replacing ties in unsigned-key traversal order.

    Entries represent one completed map, with unique nonzero keys. None means
    native null result, not a fallback profile or retained previous selection.
    The native resolver does not validate missing profiles for its consumer.
    """
    values={}
    for entry in entries:
        key=_key(entry['profile_key'])
        if key in values:
            raise ValueError('Expected unique map keys; accumulate contributions first')
        values[key]=f32(entry['volume'])
    winner=None;maximum=-1.0
    for key in sorted(values):
        if values[key] >= maximum:
            winner=key;maximum=values[key]
    return dict(profile_key=winner,comparison_volume=maximum)
