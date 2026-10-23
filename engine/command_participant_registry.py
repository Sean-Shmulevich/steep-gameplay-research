"""Recovered logical participant registration/removal on caller-owned storage.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, participant membership operations.
No native registration, allocation, locking, lifetime pinning or safe unload.
"""

def _entries(entries, participant):
    values=list(entries)
    if any(type(x) is not int or not 0<=x<2**64 for x in [*values,participant]):
        raise ValueError('uint64 identities required')
    if len(values)>0x3fff:raise ValueError('unsupported registry length')
    return values


def register_participant(entries, participant, *, capacity):
    values=_entries(entries,participant)
    if type(capacity) is not int or not len(values)<=capacity<=0x3fff:
        raise ValueError('valid supplied capacity required')
    if participant in values:return dict(entries=values,changed=False)
    if len(values)==capacity:
        raise ValueError('native allocation/growth outside this logical model')
    values.append(participant)
    return dict(entries=values,changed=True)


def remove_participant(entries, participant):
    values=_entries(entries,participant)
    try:index=values.index(participant)
    except ValueError:return dict(entries=values,changed=False)
    values[index]=values[-1];values.pop()
    return dict(entries=values,changed=True)
