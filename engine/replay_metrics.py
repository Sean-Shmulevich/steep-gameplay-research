"""Recovered local replay distance/bounds policy; see LIVE_REPLAY_LEADS.md.

The input is decoded state vectors[0], extended with its serialized zero lane.
No metres, elapsed time, player identity, or physical speed are inferred.
"""
import math
from .replay_spatial import f32


def update_metrics(point, *, existing_count, previous_point, lower, upper):
    """Return distance and new bounds, without appending or mutating records.

    Native allocation/append and optional last-record callbacks are excluded.
    Bounds are uninitialized only when BOTH four-lane endpoints are all zero.
    """
    if type(existing_count) is not int or existing_count < 0:
        raise ValueError('Nonnegative existing record count required')
    def lanes(value):
        if not isinstance(value,(list,tuple)) or len(value)!=4:
            raise ValueError('Four lanes required')
        result=[f32(x) for x in value]
        if not all(math.isfinite(x) for x in result):
            raise ValueError('Finite lanes required')
        return result
    point,lower,upper=lanes(point),lanes(lower),lanes(upper)
    distance=0.0
    if existing_count>1:
        previous=lanes(previous_point)
        delta=[f32(x-y) for x,y in zip(point,previous)]
        squares=[f32(x*x) for x in delta]
        total=f32(f32(squares[0]+squares[2])+f32(squares[1]+squares[3]))
        distance=f32(math.sqrt(total))
    if all(x==0 for x in lower+upper):
        lower,upper=point[:],point[:]
    else:
        lower=[min(x,y) for x,y in zip(lower,point)]
        upper=[max(x,y) for x,y in zip(upper,point)]
    return {'distance':distance,'lower':lower,'upper':upper}
