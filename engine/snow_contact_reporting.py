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


def accumulate_contact_bucket(buckets, record, frame_columns):
    """Local weighted bucket fold in RVA 0x140c5f1..0x140c6a9.

    Supply two unnormalized buckets and four native frame columns. Positive
    weight controls admission independently of enabled/kind/report eligibility.
    Classification uses transformed point Y; accumulation uses original vectors.
    Final averaging, normal normalization and fallback are separate operations.
    """
    if len(buckets) != 2 or len(frame_columns) != 4:
        raise ValueError('Expected two buckets and four frame columns')
    out=deepcopy(buckets)
    weight=f32(record['weight'])
    if weight <= 0:
        return out
    columns=[four(v) for v in frame_columns]
    point=four(record['point']); normal=four(record['normal'])
    y=f32(f32(point[2]*columns[2][1])+columns[3][1])
    y=f32(y+f32(point[1]*columns[1][1]))
    y=f32(y+f32(point[0]*columns[0][1]))
    bucket=out[int(y <= 0)]
    bucket['count']=(bucket['count']+1)&0xffffffff
    bucket['weight']=f32(weight+f32(bucket['weight']))
    bucket['weighted_value']=f32(f32(f32(record['value'])*weight)+f32(bucket['weighted_value']))
    for key,value in [('point',point),('normal',normal)]:
        bucket[key]=[f32(f32(weight*x)+old) for x,old in zip(value,four(bucket[key]))]
    return out


def contact_up_rotation(normal, reciprocal_sqrt_seed):
    """Fixed +Z-source specialization of RVA 0x292a40, threshold float32(1e-5).

    Returns the native unnormalized quaternion candidate. The opposite-direction
    fallback uses a supplied hardware reciprocal-square-root seed, preserving its
    refinement rounding. This does not assert downstream quaternion normalization.
    """
    n=four(normal)
    cross=[f32(f32(0.0*n[2])-n[1]), f32(n[0]-f32(0.0*n[2])),
           f32(f32(0.0*n[1])-f32(0.0*n[0])),0.0]
    dot=f32(f32(0.0*n[0])+f32(f32(0.0*n[1])+n[2]))
    if dot < 0 and all(abs(x) <= f32(1e-5) for x in cross):
        seed=f32(reciprocal_sqrt_seed(1.0))
        correction=f32(3.0-f32(f32(seed*1.0)*seed))
        factor=f32(correction*f32(.5*seed))
        return [0.0,factor,0.0,0.0]
    return [cross[0],cross[1],cross[2],f32(1.0+dot)]


def finalize_contact_bucket(bucket, fallback_point, reciprocal_sqrt_seed):
    """RVA 0x140c720..0x140c806 including the rotation helper.

    Input is an accumulated group. Output names the phase-dependent vector slot
    explicitly. Empty groups preserve it and the scalar, replacing only point XYZ.
    Finite model rejects nonempty zero-weight/zero-normal cases instead of inventing
    native NaN recovery. Seed callback is required for native rounding comparisons.
    """
    count=bucket['count']
    if type(count) is not int or not 0 <= count <= 0xffffffff:
        raise ValueError('Expected uint32 count')
    vector=four(bucket['normal']);point=four(bucket['point'])
    weight=f32(bucket['weight']);value=f32(bucket['weighted_value'])
    if count == 0:
        point=four(fallback_point);point[3]=0.0
        kind='preserved'
    else:
        squared=norm_squared(vector)
        if weight == 0 or squared <= 0:
            raise ValueError('Finite finalizer requires nonzero weight and normal')
        inverse=f32(1.0/weight)
        value=f32(inverse*value)
        point=[f32(inverse*x) for x in point]
        seed=f32(reciprocal_sqrt_seed(squared))
        factor=f32(f32(3.0-f32(f32(seed*squared)*seed))*f32(.5*seed))
        normal=[f32(factor*x) for x in vector]
        vector=contact_up_rotation(normal,reciprocal_sqrt_seed)
        kind='rotation_candidate'
    return dict(count=count,weight=weight,value=value,point=point,
                vector_slot=vector,vector_slot_kind=kind)
