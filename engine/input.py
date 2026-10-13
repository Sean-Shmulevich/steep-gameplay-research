"""Explicit immutable-per-tick input snapshots; generation is our design."""
import math
AXES={'steer','flip','lean'}
BUTTONS={'brake','tuck','jump','grab'}
def validate(actions):
    if not isinstance(actions,dict) or set(actions)-(AXES|BUTTONS):raise ValueError("Unknown input action")
    result={k:0. for k in AXES};result.update({k:False for k in BUTTONS})
    for k,v in actions.items():
        if k in AXES:
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>1:raise ValueError("Axis outside [-1,1]")
        elif not isinstance(v,bool):raise ValueError("Button must be boolean")
        result[k]=v
    return result
