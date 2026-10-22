"""One attempt of the indirect-transform accessor's reader protocol.

Evidence: CENTRAL_IMPULSE.md, Indirect transform copy and shared return storage.
Counts are supplied observations. This model neither locks nor pins live data.
"""


def plan_transform_access(count, same_owner, owner_active, atomic_count=None):
    if any(type(x) is not bool for x in (same_owner, owner_active)):
        raise ValueError('boolean owner predicates required')
    for x in (count, atomic_count):
        if x is not None and (type(x) is not int or not 0 <= x < 2**32):
            raise ValueError('uint32 reader word required')
    if count is None:
        raise ValueError('reader word required')
    if same_owner and owner_active:
        return dict(outcome='copy', count_during=(count+1)&0xffffffff,
                    count_after=count, path='owner')
    if count & 0x7ff00000:
        return dict(outcome='retry', count_during=None, count_after=count, path='busy')
    before = count if atomic_count is None else atomic_count
    after = (before+1)&0xffffffff
    if after & 0x7ff00000:
        return dict(outcome='retry', count_during=None, count_after=before, path='raced')
    return dict(outcome='copy', count_during=after, count_after=before, path='reader')


def plan_transform_write(count, owner, current_thread, owner_active, depth,
                         event_flags, atomic_count=None):
    """One writer attempt and normal publication return; dispatch is opaque.

    A wait outcome is not cancellation: wait_readers retains its writer claim.
    The model exposes unusual input states without claiming they are reachable.
    """
    for x in (count, owner, current_thread, depth, event_flags):
        if type(x) is not int or not 0 <= x < 2**32:
            raise ValueError('uint32 writer state required')
    if type(owner_active) is not bool:
        raise ValueError('boolean owner flag required')
    if atomic_count is not None and (type(atomic_count) is not int or not 0 <= atomic_count < 2**32):
        raise ValueError('uint32 atomic word required')
    word = count
    bypass = owner == current_thread and owner_active
    if not bypass:
        if word & 0x7ff00000:
            return dict(outcome='retry', count_after=word, owner_after=owner,
                        depth_after=depth, publication=None)
        before = word if atomic_count is None else atomic_count
        word = (before+0x100000)&0xffffffff
        if word & 0x7ff00000 != 0x100000:
            return dict(outcome='retry', count_after=before, owner_after=owner,
                        depth_after=depth, publication=None)
        if word & 0xfffff:
            return dict(outcome='wait_readers', count_after=word, owner_after=owner,
                        depth_after=depth, publication=None)
        owner = current_thread
    publication = dict(count=word, owner=owner, depth=(depth+1)&0xffffffff,
                       flags=event_flags & 0xfffffffd)
    # Native increments before dispatch and decrements after its normal return.
    if depth == 0:
        owner = 0xffffffff
        word = (word-0x100000)&0xffffffff
    return dict(outcome='published', count_after=word, owner_after=owner,
                depth_after=depth, publication=publication)


def initial_transform_access_state():
    """Synchronization fields written by the recovered initialization leaf.

    owner_active in the earlier planners means this bypass-enabled byte, not
    a live writer indicator. Actual ownership uses owner and depth.
    """
    return dict(reader_word=0, owner=0xffffffff, depth=0, owner_bypass_enabled=1)


def plan_accessor_cleanup(accessor_present, descriptor_valid, children_present,
                          sibling_present):
    """Post-unlink cleanup gates; supplied predicates reflect service results.

    Reader count is deliberately absent: this routine does not inspect it.
    This is a lifecycle observation, not permission to free a live accessor.
    """
    if any(type(x) is not bool for x in (accessor_present, descriptor_valid,
                                       children_present, sibling_present)):
        raise ValueError('boolean lifecycle predicates required')
    if not accessor_present:
        return dict(calls=[],owner_slot_cleared=False)
    calls = ['unlink', 'descriptor_valid']
    free = not (descriptor_valid or children_present or sibling_present)
    if free:
        calls += ['allocation_info', 'release_descriptor_second',
                  'release_descriptor_first', 'free_accessor']
    return dict(calls=calls, owner_slot_cleared=free)


def plan_transform_teardown(accessor_present, indexed, alternate_invalidation):
    """Local teardown order with optional global-tracking branch excluded.

    Detach services are opaque. Control-record validity does not exclude the
    earlier detach calls. This is not a scheduler or lifetime guarantee.
    """
    if any(type(x) is not bool for x in (accessor_present, indexed, alternate_invalidation)):
        raise ValueError('boolean teardown predicates required')
    calls = ['detach_parent', 'detach_children'] if accessor_present else []
    if indexed:
        calls.append('invalidate_alternate' if alternate_invalidation else 'invalidate_regular')
    return calls
