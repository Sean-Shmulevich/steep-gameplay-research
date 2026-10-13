"""Documented skeletal IK limb target kernel; standard-library Python only.
This is one multi-stage solver kernel, not an equipment-specific animation graph.
"""
import math,struct,json

def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def add(a,b):return f32(f32(a)+f32(b))
def sub(a,b):return f32(f32(a)-f32(b))
def mul(a,b):return f32(f32(a)*f32(b))
def div(a,b):return f32(f32(a)/f32(b))
def clamp(x,lo,hi):return min(max(x,lo),hi)
def vadd(a,b):return tuple(add(x,y)for x,y in zip(a,b))
def vsub(a,b):return tuple(sub(x,y)for x,y in zip(a,b))
def scale(a,k):return tuple(mul(x,k)for x in a)
def dot(a,b):return add(add(mul(a[0],b[0]),mul(a[2],b[2])),mul(a[1],b[1]))
def norm(a):return f32(math.sqrt(dot(a,a)))
def unit(a):
    length=norm(a)
    if length==0:raise ValueError('runtime kernel normalizes a zero vector without a guard')
    return tuple(div(x,length)for x in a)
def cross(a,b):return (sub(mul(a[1],b[2]),mul(a[2],b[1])),sub(mul(a[2],b[0]),mul(a[0],b[2])),sub(mul(a[0],b[1]),mul(a[1],b[0])))
def normalize4(q):
    squared=add(add(mul(q[0],q[0]),mul(q[2],q[2])),add(mul(q[1],q[1]),mul(q[3],q[3])))
    if squared==0:raise ValueError('runtime quaternion normalization has no zero guard')
    n=f32(math.sqrt(squared));return tuple(div(x,n)for x in q)
def direction_quaternion(a,b):
    c=cross(a,b);w=add(f32(math.sqrt(mul(dot(a,a),dot(b,b)))),dot(a,b))
    return normalize4(c+(w,))
def rotate(q,v):
    doubled=scale(v,2.);d=dot(q[:3],doubled)
    return vsub(vadd(scale(q[:3],d),scale(vadd(cross(q[:3],doubled),scale(doubled,q[3])),q[3])),v)
def quaternion_product(a,b):
    c=cross(a[:3],b[:3])
    return tuple(add(add(mul(a[3],b[i]),mul(b[3],a[i])),c[i])for i in range(3))+(sub(mul(a[3],b[3]),dot(a[:3],b[:3])),)

ACOS_COEFFICIENTS=(.08323384821414948,.02037195861339569,.0007906295941211283,.006324297748506069)
TURN_SINE_COEFFICIENTS=(6.2831854820251465,-41.339210510253906,81.39083099365234,-71.34268188476562)
def native_acos_approx(x):
    x=f32(clamp(x,-1.,1.));u=sub(1.,abs(x));c1,c2,c3,c4=ACOS_COEFFICIENTS
    p=add(mul(add(mul(add(mul(add(mul(c4,u),c3),u),c2),u),c1),u),1.)
    halfpi=f32(1.5707963705062866);term=mul(p,f32(math.sqrt(add(u,u))))
    return sub(halfpi,mul(sub(halfpi,term),-1. if x<0 else 1.))
def native_turn_sine(x):
    x=f32(x);reduced=sub(x,float(round(x)));v=sub(.25,abs(reduced));vv=mul(v,v)
    c0,c1,c2,c3=TURN_SINE_COEFFICIENTS
    return mul(add(mul(add(mul(add(mul(c3,vv),c2),vv),c1),vv),c0),v)
def native_axis_angle(axis,angle):
    turns=mul(mul(angle,.5),.15915493667125702)
    sine=native_turn_sine(sub(turns,.25));cosine=native_turn_sine(turns)
    return scale(axis,sine)+(cosine,)

def solve_middle_target(root,middle,end,requested_middle,requested_end,
                        middle_weight,alignment_control,end_weight,mix_bias,
                        end_axis_mask=(True,True,True)):
    """Documented two-segment intermediate-target kernel, including approximations.
    Parameters are functional names; their complete game configuration producers
    are unresolved. Inputs are XYZ with a zero fourth runtime position component.
    """
    A,B,C,T,U=map(lambda v:tuple(map(f32,v)),(root,middle,end,requested_middle,requested_end))
    a,b,e,h=map(f32,(middle_weight,alignment_control,end_weight,mix_bias))
    upper_length,lower_length=norm(vsub(B,A)),norm(vsub(C,B))
    pre=sub(1.,mul(b,a))
    q=[];r=[]
    for enabled in end_axis_mask:
        masked=e if enabled else 0.
        first=mul(mul(h,pre),masked)
        weight=add(mul(sub(pre,first),masked),first)
        q.append(weight);r.append(add(sub(pre,weight),mul(b,a)))
    candidate_middle=(0.,0.,0.)
    if any(x>0 for x in r):
        candidate_middle=vadd(A,scale(unit(vsub(vadd(scale(vsub(T,B),a),B),A)),upper_length))
    candidate_end=(0.,0.,0.);bend_applied=False;bend_angle=0.
    if any(x>0 for x in q):
        end_target=vadd(C,scale(vsub(U,C),e))
        first_rotation=direction_quaternion(vsub(C,A),vsub(end_target,A))
        turned_middle=vadd(A,rotate(first_rotation,vsub(B,A)))
        requested=vadd(turned_middle,scale(vsub(T,turned_middle),a))
        backward=vsub(end_target,scale(unit(vsub(end_target,requested)),lower_length))
        candidate_end=vadd(A,scale(unit(vsub(backward,A)),upper_length))
        upper=vsub(candidate_end,A)
        lower=scale(unit(vsub(end_target,candidate_end)),lower_length)
        axis=cross(lower,upper)
        if dot(axis,axis)>0:
            bend_applied=True;axis=unit(axis)
            length_a=norm(upper);length_b=lower_length
            current_distance=min(norm(vadd(upper,lower)),add(length_a,length_b))
            target_distance=min(norm(vsub(end_target,A)),add(length_a,length_b))
            lengths_squared=add(mul(length_a,length_a),mul(length_b,length_b))
            denominator=mul(add(length_b,length_b),length_a)
            current_cos=clamp(div(sub(lengths_squared,mul(current_distance,current_distance)),denominator),-1.,1.)
            target_cos=clamp(div(sub(lengths_squared,mul(target_distance,target_distance)),denominator),-1.,1.)
            bend_angle=sub(native_acos_approx(target_cos),native_acos_approx(current_cos))
            bend=native_axis_angle(axis,bend_angle)
            result_end=vadd(candidate_end,rotate(bend,lower))
            last_rotation=direction_quaternion(vsub(result_end,A),vsub(end_target,A))
            candidate_end=vadd(A,rotate(last_rotation,upper))
    result=tuple(add(mul(candidate_end[i],q[i]),mul(candidate_middle[i],r[i]))for i in range(3))
    return dict(target=result,middle_candidate=candidate_middle,end_candidate=candidate_end,
                end_candidate_weights=q,middle_candidate_weights=r,
                bend_applied=bend_applied,bend_angle_radians=bend_angle,
                upper_length=upper_length,lower_length=lower_length)

def apply_weighted_bone_orientation(current,target,weight):
    """Documented skeletal quaternion update. No weight clamp is applied here.
    Normalized linear blend chooses the target sign from quaternion dot.
    """
    a,b=tuple(map(f32,current)),tuple(map(f32,target));w=f32(weight)
    d=add(add(mul(a[0],b[0]),mul(a[2],b[2])),add(mul(a[1],b[1]),mul(a[3],b[3])))
    sign=math.copysign(1.,d)
    mixed=tuple(add(mul(sub(mul(sign,y),x),w),x)for x,y in zip(a,b))
    desired=normalize4(mixed)
    conjugate=(-a[0],-a[1],-a[2],a[3])
    delta=quaternion_product(desired,conjugate)
    stored=quaternion_product(delta,a)
    return dict(rotation=stored,delta_rotation=delta,desired_rotation=desired)

def write_chain_pose(bone_pose,bone_indices,chain_pose):
    """Scatter seven solved transform records. None represents an unmapped bone.
    Each record contains position, rotation, and scale. Other bone data survives.
    Duplicate mappings are legal and the last corresponding record wins.
    """
    if len(bone_indices)!=7 or len(chain_pose)!=7:raise ValueError('seven chain slots required')
    result={key:dict(value)for key,value in bone_pose.items()}
    for index,record in zip(bone_indices,chain_pose):
        if index is None:continue
        result.setdefault(index,{})
        for field in ('position','rotation','scale'):result[index][field]=tuple(record[field])
    return result


def examples():
    common=((0,0,0),(.5,.5,0),(1,0,0),(.3,.7,0),(.8,.2,0))
    result=solve_middle_target(*common,.8,.3,1.,.4)
    middle_only=solve_middle_target(*common,.8,.3,0.,.4)
    assert all(math.isfinite(x)for x in result['target'])
    assert middle_only['target']==middle_only['middle_candidate']
    orientation=apply_weighted_bone_orientation((0,0,0,1),(0,0,math.sqrt(.5),math.sqrt(.5)),.5)
    record=dict(position=(1,2,3,0),rotation=(0,0,0,1),scale=(1,1,1,1))
    records=[dict(record,position=(i,0,0,0))for i in range(7)]
    written=write_chain_pose({'hip':dict(record,annotation='preserved')},
                             ['hip',None,'knee',None,'ankle',None,'hip'],records)
    assert written['hip']['position']==(6,0,0,0) and written['hip']['annotation']=='preserved'
    return {'limb_target':result,'middle_only':middle_only,
            'weighted_bone_orientation':orientation,'mapped_chain_pose':written,
            'acos_endpoints':[native_acos_approx(-1),native_acos_approx(0),native_acos_approx(1)]}
if __name__=='__main__':print(json.dumps(examples(),indent=2))
