"""Recovered soft pose-row coefficient and angle-gain preparation.

Evidence: CENTRAL_IMPULSE.md, Soft pose-row coefficient preparation.
Context scalar units and extracted-count semantics remain external.
"""
import math
from reference.central_impulse import f32


def soft_pose_row_parameters(stiffness, damping, context_scalar, context_flags):
    """Return four-lane softness and angle gain with original float32 order.

    Finite values and nonsingular divisions only; native exceptional arithmetic
    is not replaced by an invented physical fallback.
    """
    if len(stiffness)!=4 or len(damping)!=4:raise ValueError('Four lanes required')
    if type(context_flags) is not int or not 0<=context_flags<=0xffffffff:
        raise ValueError('Raw uint32 context flags required')
    k=list(map(f32,stiffness));c=list(map(f32,damping));s=f32(context_scalar)
    if not all(math.isfinite(v) for v in (k+c+[s])):raise ValueError('Finite inputs required')
    count=(context_flags>>2)&0x3fff
    if abs(s)<=f32(1e-6):
        return dict(coefficient=k,angle_gain=[f32(.4)]*4,near_zero=True,extracted_count=count)
    scaled=f32(f32(count)*s)
    if scaled==0 or not math.isfinite(scaled):raise ValueError('Nonsingular finite count-scalar product required')
    coefficients=[];gains=[]
    for a,b in zip(k,c):
        ratio=f32(a/scaled);denom=f32(ratio+b)
        if denom==0 or not math.isfinite(denom):raise ValueError('Nonsingular finite denominator required')
        value=f32(s*f32(f32(1.)/denom));gain=f32(ratio/denom)
        if not math.isfinite(value) or not math.isfinite(gain):raise ValueError('Finite output required')
        coefficients.append(value);gains.append(gain)
    return dict(coefficient=coefficients,angle_gain=gains,near_zero=False,extracted_count=count)
