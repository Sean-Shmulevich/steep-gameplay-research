"""Local KinoComponent activation decisions; external effects stay explicit.

The event trace names opaque interface/helper calls without inventing their
implementation. Registry membership, owner lookup and locking are caller-owned.
"""


def plan_kino_activation(*, requested, active, owner_is_sentinel=False,
                         world_present=True, group_contains_owner=False,
                         owner_flags=0, component_flags=0,
                         auxiliary_present=False, auxiliary_flags=0):
    for value in (requested, active, owner_is_sentinel, world_present,
                  group_contains_owner, auxiliary_present):
        if type(value) is not bool:
            raise ValueError('activation observations must be boolean')
    for value, limit in ((owner_flags, 1 << 64), (component_flags, 256),
                         (auxiliary_flags, 65536)):
        if type(value) is not int or not 0 <= value < limit:
            raise ValueError('flags outside unsigned field width')
    events = []
    if not requested:
        events.append({'operation': 'interface_140'})
    if requested != active:
        if requested:
            if not owner_is_sentinel and world_present:
                slots = ([] if group_contains_owner else [16])
                slots += [37 if owner_flags & (1 << 36) else 19, 17]
                events.extend({'operation': 'register', 'slot': slot} for slot in slots)
                active = True
                if auxiliary_present:
                    auxiliary_flags |= 0x200
        elif world_present:
            events.extend({'operation': 'remove', 'slot': slot} for slot in (16, 37, 19, 17))
            active = False
            events.append({'operation': 'post_unregister', 'argument': 0.20000000298023224})
    if not requested:
        component_flags &= 0xfe
    return dict(active=active, component_flags=component_flags,
                auxiliary_flags=auxiliary_flags, events=events)
