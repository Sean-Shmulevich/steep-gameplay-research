"""Local contact reporting leaf; no body impulse or native allocation.

Evidence: CENTRAL_IMPULSE.md, Post-submission contact reporting. Source RVA
0x1410150. The caller supplies current aggregate state and selected gate.
"""
from copy import deepcopy
from math import sqrt
from reference.central_impulse import f32
from .snow_post_pending import four


def norm_squared(v):
    squares=[f32(x*x) for x in v[:3]]
    return f32(squares[0]+f32(squares[1]+squares[2]))


def report_contact(state, record, selected_gate):
    """Finite-value local behavior. State owns authored list storage, not pointers.

    Native code has no capacity check here. This adapter appends to a Python list;
    it does not reproduce native allocation, overflow, concurrency or lifetime.
    Equal squared magnitudes preserve the previous maximum vector. W participates
    in vector copies/sums but not the XYZ magnitude calculation.
    """
    result=deepcopy(state)
    if not record['enabled'] or record['kind'] != 1 or f32(selected_gate) < 0:
        return result
    identifier=record['identifier']
    if type(identifier) is not int or not 0 <= identifier <= 65535:
        raise ValueError('Expected uint16 contact identifier')
    a,b,point=four(record['a']),four(record['b']),four(record['point'])
    aa,bb=norm_squared(a),norm_squared(b)
    result['records'].append(dict(identifier=identifier,point=point,a=a,magnitude=f32(sqrt(aa))))
    for name,vector,magnitude in [('a',a,aa),('b',b,bb)]:
        if magnitude > f32(result['max_'+name+'_squared']):
            result['max_'+name+'_squared']=magnitude
            result['max_'+name]=vector[:]
        result['sum_'+name]=[f32(x+y) for x,y in zip(four(result['sum_'+name]),vector)]
    return result
