"""Recovered array-order world-stage rewiring for inactive dependency lists.

This is a topology inspection model. Native clear may alternate-release an active
list; those request/hold effects require the scheduler model, not this function.
No memory access, object retention, deduplication or concurrent mutation occurs.
"""


def rebuild_world_stage(seed, handles, wrappers, outgoing, *, lists_active=False):
    """Return a copied topology after seed/eligible terminal outgoing-list clears.

    Handles are (logical world name or None, uint32 status). Wrappers map world
    names to (entry, terminal) names. Bit 31 permits resolution. Preserve duplicate
    worlds and their repeated clears; do not silently repair the native input.
    Bounds and rejecting active lists are inspection-API policy.
    """
    if lists_active is not False:
        raise ValueError('inactive dependency lists required')
    if not isinstance(handles, (list, tuple)) or len(handles) > 65535:
        raise ValueError('at most 65535 handles required')
    def name(value):
        if not isinstance(value, str) or not value:
            raise ValueError('nonempty logical name required')
        return value
    name(seed)
    if not isinstance(wrappers, dict) or not isinstance(outgoing, dict):
        raise ValueError('wrapper and outgoing mappings required')
    links = {}
    for source, targets in outgoing.items():
        name(source)
        if not isinstance(targets, (list, tuple)):
            raise ValueError('outgoing lists required')
        links[source] = [name(target) for target in targets]
    selected = []
    for world, status in handles:
        if type(status) is not int or not 0 <= status < 2**32:
            raise ValueError('uint32 handle status required')
        if world is None or not status & 0x80000000:
            continue
        name(world)
        pair = wrappers.get(world)
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError('eligible world requires entry and terminal')
        selected.append((world, name(pair[0]), name(pair[1])))
    cleared = [seed]
    links[seed] = []
    tail = seed
    for world, entry, terminal in selected:
        links[terminal] = []
        cleared.append(terminal)
        links.setdefault(tail, []).append(entry)
        tail = terminal
    return dict(tail=tail, eligible_worlds=[row[0] for row in selected],
                cleared=cleared, outgoing=links, active_release_modeled=False)
