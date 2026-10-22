"""Recovered finite-domain directional ramp with explicit clock and curve inputs.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Directional ramp timing and transitions.
Clock ticks are divided by 1000 as observed; their physical unit is unresolved.
"""
from dataclasses import dataclass
import math
import struct


def f32(x):
    if type(x) not in (int,float) or not math.isfinite(x):raise ValueError('finite float32 value required')
    try:r=struct.unpack('<f',struct.pack('<f',x))[0]
    except (OverflowError,struct.error) as exc:raise ValueError('float32 overflow') from exc
    if not math.isfinite(r):raise ValueError('float32 overflow')
    return r

EPSILON=f32(1e-5)


def clock_scalar(ticks):
    """Emulate signed conversion plus 2^64 correction, then float32 / 1000."""
    if ticks is None:return 0.0
    if type(ticks) is not int or not 0<=ticks<1<<64:raise ValueError('uint64 clock or None required')
    signed=ticks if ticks<1<<63 else ticks-(1<<64)
    magnitude=abs(signed);shift=max(0,magnitude.bit_length()-24)
    if shift:
        q,remainder=divmod(magnitude,1<<shift);half=1<<(shift-1)
        q+=remainder>half or (remainder==half and q&1)
        magnitude=q<<shift
    result=float(-magnitude if signed<0 else magnitude)
    if signed<0:result=f32(result+float(1<<64))
    return f32(result/1000.0)

@dataclass(frozen=True)
class AxisRampState:
    current: int
    remembered: int
    timer: float

    def __post_init__(self):
        if any(type(x) is not int or not 0<=x<1<<32 for x in (self.current,self.remembered)):
            raise ValueError('uint32 state values required')
        f32(self.timer)


def transition_axis(value,state):
    """States 0/1/2 denote negative/neutral/positive for observed normal states."""
    value=f32(value);current,remembered,timer=state.current,state.remembered,f32(state.timer)
    if abs(value)<=EPSILON:
        if current!=1:remembered,current=current,1
    elif value>0:
        if current!=2:
            current=2
            if remembered==0:timer=0.0
            remembered=current
    elif current!=0:
        current=0
        if remembered==2:timer=0.0
        remembered=current
    return AxisRampState(current,remembered,timer)


def ramp_axes(vector,states,*,duration,axis_mode,previous_clock,start_ticks,end_ticks,
              curve,active=True,configuration_available=True):
    """Explicit curve callback, positive duration, detached state; no guessed curve.

    count comes from states. Axis 0 uses X; all subsequent entries use Y.
    Mode 2 skips X; mode 1 skips only entry 1. Bypassed entries retain state.
    """
    if len(vector)!=4:raise ValueError('four lanes required')
    output=[f32(x) for x in vector];states=tuple(states)
    if len(states)>65535 or any(not isinstance(s,AxisRampState) for s in states):raise ValueError('uint16 state array required')
    if type(axis_mode) is not int or not 0<=axis_mode<1<<32:raise ValueError('uint32 mode required')
    if type(active) is not bool or type(configuration_available) is not bool:raise ValueError('explicit gates required')
    previous_clock=f32(previous_clock)
    if not active or not configuration_available:
        return {'output':output,'states':states,'clock':previous_clock,'curve_inputs':()}
    duration=f32(duration)
    if duration<=0:raise ValueError('positive duration domain required')
    elapsed=f32(clock_scalar(start_ticks)-previous_clock)
    result=list(states);queries=[]
    for i,state in enumerate(states):
        if (i==0 and axis_mode==2) or (i==1 and axis_mode==1):continue
        lane=0 if i==0 else 1
        state=transition_axis(output[lane],state)
        value=f32(state.timer-elapsed) if state.current==1 else f32(elapsed+state.timer)
        timer=0.0 if value<0 else min(duration,value)
        sign_state=state.remembered if state.current==1 else state.current
        sign=1.0 if sign_state==2 else -1.0
        phase=f32(timer/duration)
        if abs(phase)<=EPSILON:shaped=0.0
        else:
            queries.append(phase);shaped=f32(curve(phase))
        output[lane]=f32(shaped*sign)
        result[i]=AxisRampState(state.current,state.remembered,timer)
    return {'output':output,'states':tuple(result),'clock':clock_scalar(end_ticks),'curve_inputs':tuple(queries)}
