"""Recovered direct child unlink, including clearing a nonmember's next link.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Child unlink and cleanup.
Cycle/missing-node rejection is authored inspection policy, not native behavior.
"""
from .transform_access import plan_accessor_cleanup


def unlink_child(head, next_links, child):
    links=dict(next_links)
    if child is None or child not in links:raise ValueError('nonnull child with supplied accessor link required')
    removed=False
    if head==child:
        head=links[child];removed=True
    elif head is not None:
        current=head;seen=set()
        while current is not None:
            if current in seen or current not in links:
                raise ValueError('cyclic or incomplete supplied child topology')
            seen.add(current);following=links[current]
            if following==child:
                links[current]=links[child];removed=True;break
            current=following
    links[child]=None
    return dict(head=head,next_links=links,removed=removed)


def unlink_and_plan_cleanup(*, accessor_present, head, next_links, child,
                            descriptor_valid, sibling_present):
    if any(type(v) is not bool for v in (accessor_present,descriptor_valid,sibling_present)):
        raise ValueError('explicit cleanup predicates required')
    result=(unlink_child(head,next_links,child) if accessor_present else
            dict(head=head,next_links=dict(next_links),removed=False))
    result['cleanup']=plan_accessor_cleanup(accessor_present,descriptor_valid,
                                            result['head'] is not None,sibling_present)
    return result


def descriptor_is_valid(*, mode, first_target, first_status, second_target,
                        second_status, index, tls_mask):
    """Recovered mode/visibility predicate; values are supplied observations.

    The mask is a uint64 bitmask, not a boolean override. This predicate does
    not retain a holder or prove that a nonzero target is safe to dereference.
    """
    for value in (mode,first_status,second_status):
        if type(value) is not int or not 0<=value<2**32:raise ValueError('uint32 mode/status required')
    for value in (first_target,second_target,tls_mask):
        if type(value) is not int or not 0<=value<2**64:raise ValueError('uint64 target/mask required')
    if type(index) is not int or not 0<=index<=65535:raise ValueError('uint16 descriptor index required')
    if mode==1:target,status=first_target,first_status
    elif mode==2 and index!=65535:target,status=second_target,second_status
    else:return False
    mask=(0xffffffffffffffff if status & 0x80000000 else 0)|tls_mask
    return bool(target & mask)


def plan_descriptor_detach(*, mode, first_target, first_status, second_target,
                           second_status, index, tls_mask):
    """Recovered dispatch only; callers must establish validity and lifetime.

    Unlike descriptor_is_valid, this dispatcher does not test the index sentinel
    or reject a zero masked target. No actual call or pointer dereference occurs.
    Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Descriptor detach dispatch.
    """
    # Share the supplied-value contract, not the validity decision.
    descriptor_is_valid(mode=mode,first_target=first_target,first_status=first_status,
                        second_target=second_target,second_status=second_status,
                        index=index,tls_mask=tls_mask)
    if mode==1:target,status,service=first_target,first_status,'direct_cleanup'
    elif mode==2:target,status,service=second_target,second_status,'indexed_detach'
    else:return dict(service=None,masked_target=None,index_forwarded=None)
    mask=(0xffffffffffffffff if status & 0x80000000 else 0)|tls_mask
    return dict(service=service,masked_target=target & mask,
                index_forwarded=index if mode==2 else None)
