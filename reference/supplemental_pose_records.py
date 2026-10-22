"""Recovered equal-count supplemental record update with supplied rotation service.

Evidence: CENTRAL_IMPULSE.md, Equal-count supplemental pose records.
Record meaning and native storage lifetime remain external. Rotation helpers
are reconstructed below with an explicit approximation-seed policy.
"""
from copy import deepcopy
from reference.central_impulse import f32


def update_equal_supplemental_records(first, second, destination, weight, rotate):
    """Mode-0 equal-source-count branch; immutable output is authored policy."""
    if len(first) != len(second):
        raise ValueError('unequal-source branch requires separate reconstruction')
    if len(first) > 255:
        raise ValueError('bounded inspection refuses native byte-counter wrap')
    output = deepcopy(destination)
    if len(destination) != len(first): return output
    w = f32(weight)
    for i, (a, b) in enumerate(zip(first, second)):
        if a['id'] != b['id']: continue
        if len(a['vector']) != 4 or len(b['vector']) != 4:
            raise ValueError('four-lane vectors required')
        av,bv = tuple(map(f32,a['vector'])),tuple(map(f32,b['vector']))
        output[i]['vector'] = [f32(f32(f32(y-x)*w)+x) for x,y in zip(av,bv)]
        output[i]['rotation'] = list(rotate(a['rotation'],b['rotation'],w))
    return output


def blend_supplemental_rotation(first, second, weight, reciprocal_sqrt, fallback):
    """Recovered rotation dispatcher and normalized-linear branch.

    Evidence: CENTRAL_IMPULSE.md, Supplemental rotation branch selection.
    Approximate reciprocal-square-root seed and fallback are explicit services.
    """
    import math
    a,b = tuple(map(f32,first)),tuple(map(f32,second))
    if len(a)!=4 or len(b)!=4 or not all(math.isfinite(x) for x in (*a,*b,weight)):
        raise ValueError('finite quaternion lanes and weight required')
    def sum4(v): return f32(f32(v[1]+v[3])+f32(v[0]+v[2]))
    dot = sum4([f32(x*y) for x,y in zip(a,b)])
    if abs(f32(abs(dot)-1.0)) <= f32(2**-23):
        return dict(rotation=list(a), branch='retain_first')
    w = f32(weight)
    if dot < f32(0.9893559813499451):
        adjusted = tuple(-x for x in b) if dot < 0 else b
        return dict(rotation=list(fallback(a,adjusted,w)),branch='fallback')
    candidate = [f32(f32(f32(1-w)*x)+f32(w*y)) for x,y in zip(a,b)]
    length2 = sum4([f32(x*x) for x in candidate])
    if not math.isfinite(length2) or length2 <= 0:
        raise ValueError('positive finite normalization length required')
    seed = f32(reciprocal_sqrt(length2))
    factor = f32(f32(3-f32(f32(seed*length2)*seed))*f32(.5*seed))
    return dict(rotation=[f32(x*factor) for x in candidate],branch='normalized_linear')


def polynomial_rotation_blend(first, second, weight, reciprocal_sqrt):
    """Recovered polynomial-weighted normalized blend, not exact SLERP.

    Evidence: CENTRAL_IMPULSE.md, Polynomial rotation fallback.
    Supplied seed preserves the native reciprocal-square-root boundary.
    """
    import math
    a,b=tuple(map(f32,first)),tuple(map(f32,second));t=f32(weight)
    if len(a)!=4 or len(b)!=4 or not all(math.isfinite(x) for x in (*a,*b,t)):
        raise ValueError('finite quaternion lanes and weight required')
    def sum4(v): return f32(f32(v[1]+v[3])+f32(v[0]+v[2]))
    dot=sum4([f32(x*y) for x,y in zip(a,b)])
    k=f32(1-f32(f32(0.8227968811988831)*dot))
    k=f32(f32(k*k)*f32(0.5854921936988831))
    s=f32(1-t)
    def polynomial(x):
        return f32(f32(f32(f32(f32(x+x)-3)*f32(x*k))+f32(k+1))*x)
    adjusted=polynomial(t) if t<=.5 else f32(1-polynomial(s))
    target=tuple(-x for x in b) if dot<0 else b
    candidate=[f32(f32(adjusted*f32(y-x))+x) for x,y in zip(a,target)]
    n=sum4([f32(x*x) for x in candidate])
    if not math.isfinite(n) or n<=0: raise ValueError('positive finite length required')
    seed=f32(reciprocal_sqrt(n))
    factor=f32(f32(3-f32(f32(seed*n)*seed))*f32(.5*seed))
    return [f32(factor*x) for x in candidate]


def evaluate_equal_supplemental_records(first, second, destination, weight, reciprocal_sqrt):
    """Joined equal-count update with reconstructed rotation helpers.

    Evidence: CENTRAL_IMPULSE.md, Joined supplemental record evaluation.
    Seed policy is supplied; no claim of native cross-hardware equivalence.
    """
    def fallback(a,b,w):
        return polynomial_rotation_blend(a,b,w,reciprocal_sqrt)
    def rotate(a,b,w):
        return blend_supplemental_rotation(a,b,w,reciprocal_sqrt,fallback)['rotation']
    return update_equal_supplemental_records(first,second,destination,weight,rotate)


def evaluate_supplemental_records(first, second, destination, weight, reciprocal_sqrt):
    """Recovered mode-0 equal/unequal-count supplemental evaluation.

    Evidence: CENTRAL_IMPULSE.md, Unequal-count supplemental source selection.
    Destination metadata is retained. Native aliases and lifetimes unmodeled.
    """
    if max(len(first),len(second)) > 255:
        raise ValueError('bounded inspection refuses native byte-counter wrap')
    if len(first)==len(second):
        return evaluate_equal_supplemental_records(first,second,destination,weight,reciprocal_sqrt)
    output=deepcopy(destination)
    if len(destination)!=max(len(first),len(second)): return output
    selected=first if first else second
    t=f32(weight) if first else f32(1-f32(weight))
    def fallback(a,b,w): return polynomial_rotation_blend(a,b,w,reciprocal_sqrt)
    for i,record in enumerate(selected):
        vector=tuple(map(f32,record['vector']))
        if len(vector)!=4: raise ValueError('four-lane vector required')
        output[i]['vector']=[f32(f32(f32(0-x)*t)+x) for x in vector]
        output[i]['rotation']=blend_supplemental_rotation(record['rotation'],[0,0,0,1],
            t,reciprocal_sqrt,fallback)['rotation']
    return output


def plan_supplemental_copy(mode, weight, requested_mask, first_count, second_count,
                           first_mask, second_mask, destination_identity='destination'):
    """Recovered mode-1/2/3 copy gate; actual allocation/copy remains external.

    Evidence: CENTRAL_IMPULSE.md, Supplemental copy gating.
    Identities are logical labels, not native pointers.
    """
    import math
    if type(mode) is not int or mode not in (1,2,3):
        raise ValueError('copy mode 1, 2 or 3 required')
    if any(type(x) is not int or not 0 <= x <= 65535
           for x in (requested_mask,first_count,second_count,first_mask,second_mask)):
        raise ValueError('uint16 counts and masks required')
    if destination_identity not in ('destination','first','second'):
        raise ValueError('known logical destination identity required')
    w=f32(weight)
    if not math.isfinite(w): raise ValueError('finite weight required')
    source='first' if mode==2 or (mode==1 and w<.5) else 'second'
    count,mask=(first_count,first_mask) if source=='first' else (second_count,second_mask)
    reason='empty' if count==0 else 'mask_miss' if not mask & requested_mask else 'same_object' if destination_identity==source else 'copy'
    return dict(source=source,copy=reason=='copy',reason=reason)


def copy_supplemental_storage(storage, source_base, destination_base, count, capacity):
    """Recovered existing-capacity copy with ordered 16-byte transfers.

    Evidence: CENTRAL_IMPULSE.md, Supplemental copy with retained capacity.
    Logical shared byte storage models overlaps. Allocation is not emulated.
    """
    if type(storage) is not bytes:
        raise ValueError('supplied immutable byte storage required')
    if any(type(x) is not int or x<0 for x in (source_base,destination_base,count,capacity)):
        raise ValueError('nonnegative integer bounds required')
    if not count<=capacity<=0x3fff:
        raise ValueError('existing capacity must fit source count')
    if source_base%16 or destination_base%16:
        raise ValueError('aligned logical source and destination required')
    if max(source_base,destination_base)+count*48>len(storage):
        raise ValueError('copy exceeds supplied storage')
    result=bytearray(storage)
    for i in range(count):
        for offset in (0,16,32):
            src=source_base+i*48+offset;dst=destination_base+i*48+offset
            result[dst:dst+16]=result[src:src+16]
    return dict(storage=bytes(result),count=count,capacity=capacity)


def plan_supplemental_reserve(control_word, requested_capacity, force=False, old_present=True):
    """Recovered reserve selection and successful replacement metadata.

    Evidence: CENTRAL_IMPULSE.md, Supplemental reserve ownership and relocation.
    Allocation success is an external precondition, not simulated here.
    """
    if type(control_word) is not int or not 0<=control_word<2**32:
        raise ValueError('uint32 control word required')
    if type(requested_capacity) is not int or not 0<=requested_capacity<=0x3fff:
        raise ValueError('14-bit capacity required')
    if type(force) is not bool or type(old_present) is not bool:
        raise ValueError('boolean force and presence required')
    capacity=control_word & 0x3fff; count=control_word>>16
    replace=force or capacity<requested_capacity
    return dict(replace=replace,relocation_bytes=count*48 if replace else 0,
                release_old=replace and old_present and not bool(control_word & 0x8000),
                control_word=(count<<16)|requested_capacity if replace else control_word)


def plan_supplemental_rebuild(control_word, source_count, old_present=True):
    """Recovered copy count-reset followed by reserve and ordered append.

    Evidence: CENTRAL_IMPULSE.md, Growing supplemental copy integration.
    Allocation success and distinct source container are preconditions.
    """
    if type(source_count) is not int or not 0<=source_count<=0x3fff:
        raise ValueError('bounded source count required')
    if type(control_word) is not int or not 0<=control_word<2**32:
        raise ValueError('uint32 control word required')
    reserve=plan_supplemental_reserve(control_word & 0xffff,source_count,
                                      old_present=old_present)
    return dict(reserve=reserve,final_control_word=reserve['control_word'] | (source_count<<16),
                append_count=source_count)


def spherical_auxiliary_rotation(first, second, weight, angle_epsilon,
                                 arccos, sine, reciprocal_sqrt):
    """Recovered auxiliary fallback with explicit transcendental/rsqrt services.

    Evidence: CENTRAL_IMPULSE.md, Auxiliary rotation uses a spherical fallback.
    Supplied math services avoid claiming host-libm bit equivalence.
    """
    import math
    a,b=tuple(map(f32,first)),tuple(map(f32,second))
    t,epsilon=f32(weight),f32(angle_epsilon)
    if len(a)!=4 or len(b)!=4 or not all(math.isfinite(x) for x in (*a,*b,t,epsilon)):
        raise ValueError('finite four-lane rotations and parameters required')
    def sum4(v):return f32(f32(v[1]+v[3])+f32(v[0]+v[2]))
    dot=sum4([f32(x*y) for x,y in zip(a,b)])
    if not -1 < dot < 1:return list(b)
    theta=f32(arccos(abs(dot)))
    left=f32(sine(f32(f32(1-t)*theta)))
    right=f32(sine(f32(theta*t)))
    if dot<0:right=-right
    if epsilon>=abs(theta):return list(b)
    inverse=f32(1/f32(sine(theta)))
    left,right=f32(left*inverse),f32(right*inverse)
    candidate=[f32(f32(left*x)+f32(right*y)) for x,y in zip(a,b)]
    n=sum4([f32(x*x) for x in candidate])
    if not math.isfinite(n) or n<=0:raise ValueError('positive finite length required')
    seed=f32(reciprocal_sqrt(n))
    factor=f32(f32(3-f32(f32(seed*n)*seed))*f32(.5*seed))
    return [f32(x*factor) for x in candidate]


def blend_auxiliary_rotation(first, second, weight, arccos, sine, reciprocal_sqrt):
    """Recovered auxiliary dispatcher, with original-sign spherical fallback.

    Evidence: CENTRAL_IMPULSE.md, Complete auxiliary triplet evaluation.
    Services preserve explicit math-library and instruction approximation bounds.
    """
    import math
    a,b=tuple(map(f32,first)),tuple(map(f32,second));t=f32(weight)
    if len(a)!=4 or len(b)!=4 or not all(math.isfinite(x) for x in (*a,*b,t)):
        raise ValueError('finite four-lane rotations and weight required')
    def sum4(v):return f32(f32(v[1]+v[3])+f32(v[0]+v[2]))
    dot=sum4([f32(x*y) for x,y in zip(a,b)])
    if abs(f32(abs(dot)-1))<=f32(2**-23):
        return dict(rotation=list(a),branch='retain_first')
    if dot<f32(0.9893559813499451):
        return dict(rotation=spherical_auxiliary_rotation(a,b,t,f32(1e-5),
                    arccos,sine,reciprocal_sqrt),branch='spherical')
    candidate=[f32(f32(f32(1-t)*x)+f32(t*y)) for x,y in zip(a,b)]
    n=sum4([f32(x*x) for x in candidate])
    if not math.isfinite(n) or n<=0:raise ValueError('positive finite length required')
    seed=f32(reciprocal_sqrt(n))
    factor=f32(f32(3-f32(f32(seed*n)*seed))*f32(.5*seed))
    return dict(rotation=[f32(x*factor) for x in candidate],branch='normalized_linear')
