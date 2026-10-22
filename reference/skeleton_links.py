"""Linked-skeleton pruning with supplied resolution outcomes.

Evidence: CENTRAL_IMPULSE.md, Linked-skeleton pruning and unregister scope.
Only the no-eligible-child branch is modeled. This does not retain objects,
implement locking, or evaluate child poses. Service mutation is excluded.
"""


def prune_ineligible_links(entries, pending, owner_world):
    """Entries are unique synthetic IDs and states: unresolved/worldless/no_skeleton.

    Returns retained order and opaque service calls while the list lock is held.
    Inputs describe resolved outcomes, not pointer validity guarantees.
    """
    if type(pending) is not int or not 0 <= pending <= 255:
        raise ValueError('uint8 pending required')
    if type(owner_world) is not bool:
        raise ValueError('boolean owner_world required')
    items = [tuple(item) for item in entries]
    if len(items) > 65535 or any(len(item) != 2 for item in items):
        raise ValueError('uint16 list of ID/state pairs required')
    if any(type(i) is not int or i < 0 or state not in
           ('unresolved', 'worldless', 'no_skeleton') for i, state in items):
        raise ValueError('nonnegative ID and ineligible state required')
    if len({i for i, _ in items}) != len(items):
        raise ValueError('unique synthetic IDs required')
    calls = []
    index = 0
    while index < len(items):
        ident, state = items[index]
        if state == 'unresolved':
            if index != len(items) - 1:
                calls.append(['replace', index, len(items) - 1])
                items[index] = items[-1]
            calls.append(['destroy_last', len(items) - 1])
            items.pop()
            continue
        if state == 'no_skeleton':
            calls.append(['lookup', ident])
        index += 1
    if not items and pending & 64 and owner_world:
        calls.append(['unregister', 14])
        pending &= 191
    return dict(retained=[i for i, _ in items], pending=pending, calls=calls)


def plan_eligible_child(mode, parent_mask, parent_flags, child_flags, dirty,
                        pending, primary_present, alternate_time_group):
    """Control flow with non-mutating opaque services and inline scratch storage.

    Child flags/pending are outputs before opaque refresh. Actual preparation,
    advance and refresh may mutate those fields: callers must not treat this
    branch plan as a complete pose evaluation. Time values remain external.
    """
    for value in (parent_flags, child_flags, dirty, pending):
        if type(value) is not int or not 0 <= value <= 255:
            raise ValueError('uint8 state required')
    if type(mode) is not int or not 0 <= mode < 2**32:
        raise ValueError('uint32 link mode required')
    if type(parent_mask) is not int or not 0 <= parent_mask <= 65535:
        raise ValueError('uint16 parent mask required')
    if type(primary_present) is not bool or type(alternate_time_group) is not bool:
        raise ValueError('boolean predicates required')
    calls = []
    scalar_override = None
    if primary_present:
        if mode == 2:
            scalar_override = -1.0
        else:
            calls.append('prepare_child')
        if parent_mask & 0x38 and parent_flags & 1:
            calls.append('prepare_scratch')
            child_flags &= 247
            calls.append('advance_alternate' if alternate_time_group else 'advance_default')
            pending |= 1
        if dirty & 128 or pending & 1:
            calls.extend(['lock_child', 'refresh_force1_secondary0', 'unlock_child'])
    return dict(calls=calls, scalar_override=scalar_override,
                child_flags=child_flags, pending=pending)
