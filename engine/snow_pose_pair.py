"""Recovered body-pair ordering used by pose-record construction.

Evidence: CENTRAL_IMPULSE.md, Pose body-pair ordering.
Body tokens identify caller-owned records, not dereferenceable pointers.
"""


def order_pose_bodies(first, second=None):
    """Return ordered tokens/keys and the constructor's frame-swap decision.

    Each supplied body has token, flags16 and key32. Bit15-set bodies precede
    bit15-clear bodies; equal flag classes sort by unsigned key, preserving ties.
    Body classes, ownership and key producer semantics remain unresolved.
    """
    for body in (first,second):
        if body is None:continue
        for name,limit in (('token',2**64),('flags16',2**16),('key32',2**32)):
            if type(body[name]) is not int or not 0<=body[name]<limit:
                raise ValueError('Unsigned body metadata required')
        if body['token']==0:raise ValueError('Use None for absent second body')
    if first is None:raise ValueError('First body required')
    if second is not None and first['token']==second['token'] and first!=second:
        raise ValueError('Aliased body metadata must agree')
    swap=False
    if second is not None:
        a=bool(first['flags16']&0x8000);b=bool(second['flags16']&0x8000)
        swap=(b and not a) or (a==b and second['key32']<first['key32'])
    ordered=(second,first) if swap else (first,second)
    return {'tokens':[x['token'] if x else 0 for x in ordered],
            'keys':[x['key32'] if x else 0 for x in ordered],
            'frame_swap':ordered[0]['token']!=first['token']}
