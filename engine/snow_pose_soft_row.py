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


def soft_pose_row_response(stiffness, damping, context_scalar, context_flags,
                           axis, reference, target, *, atan2):
    """Compose soft coefficients with angular helper; no row allocation or solve."""
    from .snow_pose_angle import pose_row_angle
    result=soft_pose_row_parameters(stiffness,damping,context_scalar,context_flags)
    angle=pose_row_angle(axis,reference,target,atan2)
    scaled=f32(angle['angle']*f32(context_scalar))
    result['angle']=angle
    result['angle_term']=[f32(scaled*g) for g in result['angle_gain']]
    return result


def build_soft_pose_row(initial_row, *, class_byte, base_row, class_count,
                        row_region_offset, result_count, stiffness, damping,
                        context_scalar, context_flags, axis, reference, target,
                        atan2):
    """Return the helper's full row writes and next counters for supplied storage.

    Relative placement is arithmetic only; no allocation or native memory access.
    Untouched bytes come from initial_row. Math-service failure is not a native
    rollback guarantee; this detached API publishes only on normal return.
    """
    import struct
    if type(class_byte) is not int or not 0<=class_byte<=255:raise ValueError('Raw class byte required')
    for value in (base_row,class_count,row_region_offset,result_count):
        if type(value) is not int or not 0<=value<=0xffffffff:raise ValueError('Raw uint32 placement fields required')
    stride=5 if class_byte else 6
    if len(initial_row)!=16*stride:raise ValueError('Initial row size must match selected class')
    relative_offset=row_region_offset+(((base_row+class_count*stride)&0xffffffff)<<4)
    response=soft_pose_row_response(stiffness,damping,context_scalar,context_flags,axis,reference,target,atan2=atan2)
    out=bytearray(initial_row)
    struct.pack_into('<I',out,4,result_count)
    struct.pack_into('<4f',out,0x10,*response['angle_term'])
    axis_bytes=struct.pack('<4f',*axis);out[0x20:0x30]=axis_bytes
    if not class_byte:
        out[0x40:0x50]=struct.pack('<4I',*(x^0x80000000 for x in struct.unpack('<4I',axis_bytes)))
    struct.pack_into('<4f',out,0x40 if class_byte else 0x50,*response['coefficient'])
    return dict(row=bytes(out),relative_offset=relative_offset,
                next_class_count=(class_count+1)&0xffffffff,
                next_result_count=(result_count+1)&0xffffffff,response=response)
