"""Recovered group-selection predicate; physical vector meanings unresolved.

Evidence: CENTRAL_IMPULSE.md, Pose group eligibility predicate.
"""
import math
from reference.central_impulse import f32


def pose_links_clear(*, body_token, blocking_link, first_link, read_link):
    """Check a retained circular list using endpoint-specific next links.

    read_link returns status32, flags8, first_body, next_first, next_second.
    Malformed cycles raise an authored error; native code has no such guard.
    """
    if blocking_link:return False
    if not first_link:return True
    current=first_link;visited=set()
    while True:
        if current in visited:raise ValueError('Link cycle did not return to its head')
        visited.add(current)
        link=read_link(current)
        if link['status32']!=0xffffffff or link['flags8']&2:return False
        current=link['next_first'] if link['first_body']==body_token else link['next_second']
        if current==first_link:return True
        if not current:raise ValueError('Circular link unexpectedly null')


def pose_group_eligible(first_vector, second_vector, first_threshold,
                        second_threshold, *, links_clear):
    """Both squared lengths strictly below squared thresholds, AND link check.

    The link service executes even when either magnitude test fails. No absolute
    value, vector normalization or positive-threshold restriction is introduced.
    """
    def vector(v):
        if len(v)!=3:raise ValueError('Three components required')
        v=list(map(f32,v))
        if not all(map(math.isfinite,v)):raise ValueError('Finite vector required')
        return v
    a,b=vector(first_vector),vector(second_vector)
    p,q=f32(first_threshold),f32(second_threshold)
    if not math.isfinite(p) or not math.isfinite(q):raise ValueError('Finite thresholds required')
    def squared(v):
        return f32(f32(f32(v[0]*v[0])+f32(v[1]*v[1]))+f32(v[2]*v[2]))
    below=squared(a)<f32(p*p)
    if below:below=squared(b)<f32(q*q)
    clear=links_clear()
    return bool(below and clear)
