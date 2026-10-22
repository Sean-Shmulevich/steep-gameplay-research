"""Recovered attachment transform setup with explicit external services.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Attachment setup read/validity order.
No allocation, linking, native pointer access or lifecycle notifications occur.
"""
from .transform_composition import compose_transform, _rows
from .transform_inverse import inverse_transform


def initialize_attachment_transform(*, current_transform, explicit_offset=None,
        get_parent, descriptor_valid, store_local, publish_entity, propagate_child,
        reciprocal_seed=None):
    """Execute the observed transform-setup phase after attachment acceptance.

    Parent reads are separate calls, not a cached atomic snapshot. Publication
    callbacks receive a packet with aliased matrix slots and flags 31. Callback
    signatures are authored. Failed validity skips storage/child dispatch only;
    earlier inversion and current-transform read have already happened.
    """
    parent = _rows(get_parent())
    if explicit_offset is not None:
        target = compose_transform(parent, explicit_offset)
        packet = dict(first_transform=target, second_transform=target, flags=31)
        publish_entity(packet)
        return 'entity_published'
    inverse = inverse_transform(parent, reciprocal_seed)
    local = compose_transform(inverse, current_transform())
    if not descriptor_valid():
        return 'descriptor_rejected'
    store_local(local)
    parent_again = _rows(get_parent())
    packet = dict(first_transform=parent_again, second_transform=parent_again, flags=31)
    propagate_child(packet)
    return 'child_propagated'


def plan_attachment_acceptance(*, child, parent, parent_link, child_owner,
                               parent_owner, permission):
    """Recovered inner acceptance checks over supplied identity tokens.

    parent_link is the parent's descriptor first-holder resolution, not a proved
    recursive root. None models null owner/link; parent and child must be nonnull.
    Outer reattachment may already have detached the child before these checks.
    Reason labels and argument validation are authored inspection conveniences.
    """
    if child is None or parent is None:
        raise ValueError('nonnull child and resolved parent required')
    if type(permission) is not bool:
        raise ValueError('boolean permission result required')
    reason = None
    if parent_link == child:
        reason = 'parent_link_is_child'
    elif parent == child:
        reason = 'self_attachment'
    elif parent_owner is not None and child_owner is not None and parent_owner != child_owner:
        reason = 'owner_mismatch'
    queried = reason is None
    if queried and not permission:
        reason = 'permission_denied'
    return dict(accepted=reason is None, permission_queried=queried, reason=reason)


def plan_entity_attachment_permission(*, child_group, parent_group, contains_other,
                                      child_bit, parent_bit):
    """Concrete entity permission effects over supplied membership/type results.

    contains_other refers only to the selected collection: child group first,
    otherwise parent group. Group resolution and flag-setter effects stay external.
    The unnamed flag is bit 35 of the entity word at +0x98 in the studied build.
    """
    if any(type(x) is not bool for x in (child_group, parent_group, contains_other)):
        raise ValueError('boolean group/membership predicates required')
    if any(type(x) is not int or x not in (0,1) for x in (child_bit,parent_bit)):
        raise ValueError('flag bits must be integer zero or one')
    events = ['collect_child'] if child_group else ['collect_parent'] if parent_group else []
    accepted = not (events and contains_other)
    if accepted and child_bit != parent_bit:
        events.append('set_child_flag')
    return dict(accepted=accepted, events=events)


def plan_attachment_flag_propagation(root, target, bits, hierarchy, skeleton_links,
                                    *, max_visits=4096):
    """Recovered traversal order over supplied stable, resolved entity graphs.

    Hierarchy children precede skeleton lookup/links. Duplicates are preserved.
    None skeleton entries model unresolved targets. Graph storage and visit bound
    are authored; native cycle termination and concurrent mutation are unproved.
    """
    if type(target) is not int or target not in (0,1):
        raise ValueError('target bit must be zero or one')
    if type(max_visits) is not int or max_visits < 1:
        raise ValueError('positive visit budget required')
    values = dict(bits)
    if any(type(x) is not int or x not in (0,1) for x in values.values()):
        raise ValueError('entity bits must be zero or one')
    events = []; stack = [('visit',root)]; visits = 0
    while stack:
        phase, entity = stack.pop()
        if phase == 'query':
            events.append(dict(event='query',entity=entity))
            stack.extend(('visit',x) for x in reversed(skeleton_links.get(entity,())) if x is not None)
            continue
        visits += 1
        if visits > max_visits:
            raise ValueError('inspection visit budget exceeded')
        if entity not in values:
            raise ValueError('resolved entity missing supplied bit')
        events.append(dict(event='visit',entity=entity))
        if values[entity] != target:
            values[entity] = target
            events.append(dict(event='cache',entity=entity))
        stack.append(('query',entity))
        stack.extend(('visit',x) for x in reversed(hierarchy.get(entity,())))
    return dict(bits=values,events=events)
