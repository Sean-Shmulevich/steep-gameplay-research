"""Recovered logical behavior of compact tagged command-key insertion.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, compact participant key set.
Models sorted uint64 keys and duplicate result, not storage allocation, tag-7
promotion, reference ownership or concurrent mutation. This is not a FIFO.
"""
from bisect import bisect_left


def compact_command_insert(keys, key):
    values=list(keys)
    if any(type(x) is not int or not 0 <= x < 2**64 for x in [*values,key]):
        raise ValueError('uint64 keys required')
    if len(values)>31 or any(a>=b for a,b in zip(values,values[1:])):
        raise ValueError('compact keys must be sorted, unique and at most 31')
    index=bisect_left(values,key)
    if index<len(values) and values[index]==key:
        return dict(keys=values,inserted=False,result=0)
    if len(values)==31:
        raise ValueError('tag-7 promotion is outside this compact model')
    values.insert(index,key)
    return dict(keys=values,inserted=True,result=1)


def compact_command_seek(keys, cursor, *, advance=False):
    """Compact first/next semantics, including cursor writes on exhaustion.

    First returns an exact cursor key if present, otherwise delegates to next.
    Next increments the uint64 cursor before lookup; max wraps to zero and ends.
    An empty zero container returns exhaustion without changing the cursor.
    Caller supplies the set for each call; no snapshot or concurrency is implied.
    """
    values=list(keys)
    # Reuse domain validation without accepting promotion as an operation.
    compact_command_insert(values, cursor if not values else values[0])
    if type(cursor) is not int or not 0 <= cursor < 2**64 or type(advance) is not bool:
        raise ValueError('uint64 cursor and boolean advance required')
    if not values:return dict(result=0,cursor=cursor)
    index=bisect_left(values,cursor)
    if not advance and index<len(values) and values[index]==cursor:
        return dict(result=1,cursor=cursor)
    following=(cursor+1)&(2**64-1)
    if cursor==2**64-1:return dict(result=0,cursor=following)
    index=bisect_left(values,following)
    return dict(result=int(index<len(values)),cursor=values[index] if index<len(values) else following)
