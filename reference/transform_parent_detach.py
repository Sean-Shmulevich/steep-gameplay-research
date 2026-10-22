"""Recovered mode-0/mode-1 parent detach under nonmutating service callbacks.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Parent detach ownership experiment.
This is an effect/count model, not a native lifetime lease or allocator.
"""


def plan_parent_detach(*, mode, visible, allow_free, sibling_present,
                       children_present, reader_word, initial_holder_count):
    """Plan the validated local branch with two distinct nonfinal holders.

    The parent accessor starts with an invalid descriptor, no next link, and
    this child at its head. The optional auxiliary notification is disabled.
    visible is the supplied descriptor visibility result. Reader-word values do
    not alter this local detach path. Callbacks must preserve the modeled state.
    Mode 2, aliased holders, last-reference retirement and concurrent operations
    remain outside this model; rejecting them is an authored adapter policy.
    """
    if type(mode) is not int or mode not in (0,1):
        raise ValueError('only validated descriptor modes 0 and 1 are supported')
    if any(type(x) is not bool for x in
           (visible,allow_free,sibling_present,children_present)):
        raise ValueError('explicit boolean predicates required')
    if type(reader_word) is not int or not 0<=reader_word<2**32:
        raise ValueError('uint32 reader word required')
    if type(initial_holder_count) is not int or not 2<=initial_holder_count<2**32-1:
        raise ValueError('nonfinal, nonoverflowing holder count required')
    detached=mode==1 and visible
    parent_freed=detached and not sibling_present
    child_freed=allow_free and not children_present and (detached or not sibling_present)
    events=[]
    def event(name,count):
        events.append(dict(event=name,first_count=count,second_count=count))
    if detached:
        event('before_detach',initial_holder_count+1)
        if parent_freed:event('free_parent_accessor',initial_holder_count+1)
        event('manager_notify',initial_holder_count+1)
    event('descriptor_reset',initial_holder_count)
    if child_freed:event('free_child_accessor',initial_holder_count)
    return dict(events=events,parent_accessor_freed=parent_freed,
                child_accessor_freed=child_freed,final_holder_count=initial_holder_count-1)
