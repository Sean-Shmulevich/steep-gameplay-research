"""Recovered keyed action-curve evaluator; cubic root solver remains explicit.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Keyed ramp curve evaluation.
Finite float32 domain. No invented easing curve or root ordering is supplied.
"""
from dataclasses import dataclass
from .action_axis_ramp import f32, EPSILON

@dataclass(frozen=True)
class CurveKey:
    x: float
    y: float
    incoming: tuple[float,float]
    outgoing: tuple[float,float]
    mode: int


def evaluate_key_curve(keys, x, *, input_bounds=None, output_bounds=None, solve_roots=None):
    """Mode 1 linear, mode 2 cubic, all other uint32 modes hold left value.

    solve_roots(c0,c1,c2,c3) returns the original-ordered roots, at most three.
    The original chooses the LAST returned root, clamps it to [0,1], or uses
    zero when no roots are returned. This is not a substitute polynomial solver.
    """
    keys=tuple(keys);x=f32(x)
    if len(keys)>65535:raise ValueError('uint16 key count required')
    normalized=[]
    for k in keys:
        if not isinstance(k,CurveKey) or type(k.mode) is not int or not 0<=k.mode<1<<32:
            raise ValueError('CurveKey with uint32 mode required')
        if len(k.incoming)!=2 or len(k.outgoing)!=2:raise ValueError('two-lane handles required')
        normalized.append(CurveKey(f32(k.x),f32(k.y),tuple(map(f32,k.incoming)),tuple(map(f32,k.outgoing)),k.mode))
    keys=tuple(normalized)
    if any(a.x>b.x for a,b in zip(keys,keys[1:])):raise ValueError('nondecreasing key positions required')
    def clamp(value,bounds):
        if bounds is None:return value
        if len(bounds)!=2:raise ValueError('two bounds required')
        lower,upper=map(f32,bounds)
        # Native MAXSS/MINSS choose the second operand on equality.
        low=lower if lower>value else value
        return upper if upper<low else low
    x=clamp(x,input_bounds)
    if not keys:return 0.0  # Original empty path bypasses output clamping.
    if x<keys[0].x:return clamp(keys[0].y,output_bounds)
    left=keys[0];right=None
    for key in keys:
        if key.x>x:right=key;break
        left=key
    if right is None or left.mode not in (1,2):result=left.y
    elif left.mode==1:
        dx=f32(right.x-left.x)
        if abs(dx)<EPSILON:result=left.y
        else:result=f32(f32(f32(f32(x-left.x)/dx)*f32(right.y-left.y))+left.y)
    else:
        if solve_roots is None:raise ValueError('cubic root solver must be supplied explicitly')
        x0,x1,x2,x3=left.x,left.outgoing[0],right.incoming[0],right.x
        coefficients=(f32(x0-x),f32(f32(x1-x0)*3),
                      f32(f32(f32(f32(x0-x1)-x1)+x2)*3),
                      f32(f32(f32(x1-x2)*3)+f32(x3-x0)))
        roots=tuple(map(f32,solve_roots(*coefficients)))
        if len(roots)>3:raise ValueError('at most three solver roots required')
        t=clamp(roots[-1],(0.,1.)) if roots else 0.
        y0,y1,y2,y3=left.y,left.outgoing[1],right.incoming[1],right.y
        a=f32(f32(y1-y0)*3);b=f32(f32(f32(y2-y1)*3)-a)
        c=f32(f32(f32(y3-y0)-a)-b)
        t2=f32(t*t);t3=f32(t2*t)
        result=f32(f32(f32(y0+f32(c*t3))+f32(b*t2))+f32(a*t))
    return clamp(result,output_bounds)
