"""Portable documented animation playback policies. Standard library only."""
from dataclasses import dataclass
import math,struct,json

def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def add(a,b):return f32(f32(a)+f32(b))
def sub(a,b):return f32(f32(a)-f32(b))
def mul(a,b):return f32(f32(a)*f32(b))
def div(a,b):return f32(f32(a)/f32(b))
EPSILON=f32(1e-5)
INVALID=f32(3.4028234663852886e38)

def inclusive_wrap(value,lower=0.,upper=1.):
    value,lower,upper=map(f32,(value,lower,upper));span=max(sub(upper,lower),0.)
    if abs(span)<=EPSILON:return lower
    if lower<=value<=upper:return value
    offset=sub(value,lower);remainder=f32(math.fmod(offset,span))
    return add(upper if offset<0 else lower,remainder)

def effective_duration(child_duration,source_multiplier):
    source=f32(source_multiplier)
    if abs(source)<=EPSILON:source=1.
    return div(child_duration,source)

def clip_phase_offset(offset_time,clip_duration):
    duration=f32(clip_duration)
    return div(offset_time,duration) if abs(duration)>EPSILON else 0.

def remap_phase_pair(start,end,offset=0.):
    first=inclusive_wrap(add(start,offset));second=inclusive_wrap(add(end,offset))
    delta=sub(second,first);crossed=delta<0
    while delta<0:delta=add(delta,1.)
    return dict(start=first,end=second,positive_delta=delta,crossed=crossed)

@dataclass
class MarkerCoordinate:
    fraction:float=0.
    first:int=0
    second:int=0

def next_cycle_marker(first,keys):
    category_mask=4160749571
    count=sum((int(key)&category_mask)==(int(first)&category_mask) for key in keys)
    return int(first)^(((int(first)&4294967292)+count*4)^int(first))&134217724

def phase_to_marker(phase,keys,durations,total_duration,looping=False,valid=True,previous=None):
    """Map global phase to an interval. Preserves keys if no interval is found.
    Packed keys are opaque caller identifiers; no gameplay marker names assumed.
    """
    p,total=f32(phase),f32(total_duration)
    result=MarkerCoordinate(**previous.__dict__) if previous else MarkerCoordinate()
    if not valid or abs(total)<=EPSILON:
        result.fraction=min(max(p,0.),1.);result.first=result.second=0;return result
    if abs(sub(p,1.))<=EPSILON:
        if looping:
            result.first=int(keys[-1]);result.second=next_cycle_marker(keys[0],keys)
        else:
            result.first,result.second=map(int,keys[-2:])
        result.fraction=1.;return result
    time=mul(total,p);accumulated=0.
    for i,length in enumerate(durations):
        boundary=add(accumulated,length)
        if time<boundary:
            result.first=int(keys[i]);result.second=int(keys[(i+1)%len(keys)])
            result.fraction=min(max(div(sub(time,accumulated),sub(boundary,accumulated)),0.),1.)
            return result
        accumulated=boundary
    result.fraction=INVALID;return result

def marker_to_phase_nonloop(coordinate,keys,durations,total_duration,valid=True,category_match=False):
    """Documented non-looping strict/category matching path. First matching pair wins.
    Full repeated-cycle marker repair is outside this function.
    """
    total=f32(total_duration)
    if not valid or abs(total)<=EPSILON:return f32(coordinate.fraction)
    mask=4160749571 if category_match else 4294967295
    accumulated=0.
    for i,length in enumerate(durations):
        if (int(keys[i])&mask)==(int(coordinate.first)&mask):
            if i+1>=len(keys):return INVALID
            if (int(keys[i+1])&mask)!=(int(coordinate.second)&mask):
                if not category_match:return INVALID
            else:return min(div(add(mul(length,coordinate.fraction),accumulated),total),1.)
        accumulated=add(accumulated,length)
    return INVALID

def sampling_schedule(start,end,positive_delta,crossed,frame_time,flags,
                      cache_invalid=True,boundary_cache_ready=False):
    """Exact AnimationDataNode boundary dispatch arithmetic with explicit gates.
    Unknown flag meanings remain numerical. This is the observed formula.
    """
    p,q,d,dt=map(f32,(start,end,positive_delta,frame_time));flags=int(flags)
    if not crossed:return [dict(start=p,delta=d,frame_time=dt,flags=flags)]
    allowed=(cache_invalid or bool(flags&1) or (bool(flags&4) and not boundary_cache_ready) or bool(flags&32))
    if not allowed:return []
    denominator=sub(1.,d)
    if denominator==0:raise ValueError('runtime boundary split divides by zero for delta=1')
    tail=sub(1.,p);first_time=mul(div(tail,denominator),dt)
    return [dict(start=p,delta=tail,frame_time=first_time,flags=flags&~32),
            dict(start=0.,delta=q,frame_time=sub(dt,first_time),flags=flags)]

def choose_transition_duration(literal_duration,variable_duration=None,override=None,use_variable=False):
    """Documented transition initializer's duration selection and clamp order.
    A variable lookup result is explicit; its key/provider remains external.
    """
    if override is not None and f32(override)!=INVALID:return f32(override)
    if use_variable:
        if variable_duration is None:raise ValueError('variable duration result required')
        return max(f32(variable_duration),0.)
    return f32(literal_duration)

def select_custom_transition(source_candidates,target_candidates):
    """Last eligible shared selector pair wins, in nested stored order.
    Records have selector,eligibility,target; source target fields are ignored.
    This selects a custom transition specification, not the global state edge.
    """
    selected=None
    for source in source_candidates:
        for target in target_candidates:
            if source['selector']==target['selector'] and source['eligibility']*target['eligibility']!=0:
                selected=dict(selector=source['selector'],target=target['target'])
    return selected


def examples():
    keys=[4,8,12];durations=[.25,.75,0.]
    coordinate=phase_to_marker(.25,keys,durations,1.)
    assert coordinate.first==8 and coordinate.fraction==0
    assert marker_to_phase_nonloop(coordinate,keys,durations,1.)==.25
    pair=remap_phase_pair(.9,.1)
    schedule=sampling_schedule(pair['start'],pair['end'],pair['positive_delta'],pair['crossed'],.016,32)
    assert effective_duration(2.,0.)==2. and effective_duration(2.,2.)==1.
    override=choose_transition_duration(2.,variable_duration=-3.,override=-.5,use_variable=True)
    variable=choose_transition_duration(2.,variable_duration=-3.,use_variable=True)
    selected=select_custom_transition([dict(selector=1,eligibility=1),dict(selector=2,eligibility=1)],
        [dict(selector=1,eligibility=1,target='first'),dict(selector=2,eligibility=1,target='last')])
    assert override==-.5 and variable==0. and selected['target']=='last'
    return dict(transition_override=override,variable_duration_clamped=variable,custom_transition=selected,
                marker_exact_boundary=coordinate.__dict__,effective_duration=1.,
                phase_pair=pair,boundary_schedule=schedule,
                inclusive_end=inclusive_wrap(1.),wrapped_end=inclusive_wrap(2.))
if __name__=='__main__':print(json.dumps(examples(),indent=2))
