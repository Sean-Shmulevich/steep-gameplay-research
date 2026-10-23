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
