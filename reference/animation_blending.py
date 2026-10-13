"""Documented animation blend blocks. Standard-library only; no game files required."""
import math,struct,json
F=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
add=lambda a,b:F(F(a)+F(b))
sub=lambda a,b:F(F(a)-F(b))
mul=lambda a,b:F(F(a)*F(b))
EPS=F(1e-5)
POLY_SCALE=F(.8227968811988831)
POLY_CURVATURE=F(.5854921936988831)

def normalize_weights(weights):
    """SimpleBlendNode clamps negatives before this normalization helper."""
    w=[F(max(0,v)) for v in weights]
    if not w:return w,0
    dominant=0;largest=-float('inf');total=0.
    for i,v in enumerate(w):
        if v>largest:dominant=i;largest=v
        total=add(total,v)
    if total<EPS:w[0]=1.;return w,dominant
    inv=F(1/total)
    return [mul(v,inv) for v in w],dominant

def incremental_blend_schedule(weights):
    """Active children are evaluated in serialized order."""
    total=0.;out=[]
    for i,w in enumerate(weights):
        w=F(w)
        if w>EPS:
            total=add(total,w)
            out.append({'child':i,'alpha':F(w/total),'accumulated_weight':total})
    return out

def axial_blend(coordinate,knots):
    """Returns neighboring indices and alpha; None alpha means exact selection."""
    if not knots:raise ValueError('At least one knot required')
    if len(knots)==1:return 0,0,None
    x=F(min(max(F(coordinate),F(knots[0])),F(knots[-1])))
    for i in range(1,len(knots)):
        right=F(knots[i]);left=F(knots[i-1])
        if x<right:
            alpha=F(min(max(F(sub(x,left)/sub(right,left)),0),1))
            if abs(alpha)<=EPS:return i-1,i-1,None
            return i-1,i,alpha
    return len(knots)-1,len(knots)-1,None

def linear_blend(a,b,weight):
    return [add(x,mul(weight,sub(y,x))) for x,y in zip(a,b)]

def normalized(q):
    norm=math.sqrt(sum(x*x for x in q))
    if norm==0:raise ValueError('Zero quaternion has no orientation')
    return [F(x/norm) for x in q]

def quaternion_product(a,b):
    x,y,z,w=a;X,Y,Z,W=b
    return [F(w*X+W*x+y*Z-Y*z),F(w*Y+W*y+z*X-x*Z),
            F(w*Z+W*z+x*Y-y*X),F(w*W-x*X-y*Y-z*Z)]

def polynomial_quaternion_blend(a,b,weight):
    """Engine polynomial approximation, signed dot before hemisphere correction."""
    a=list(map(F,a));b=list(map(F,b));t=F(weight)
    dot=add(add(mul(a[0],b[0]),mul(a[2],b[2])),add(mul(a[1],b[1]),mul(a[3],b[3])))
    k=mul(mul(sub(1,mul(POLY_SCALE,dot)),sub(1,mul(POLY_SCALE,dot))),POLY_CURVATURE)
    def low(u):return mul(add(add(mul(mul(sub(mul(2,u),3),k),u),k),1),u)
    corrected=low(t) if t<=.5 else sub(1,low(sub(1,t)))
    signed_b=[-x for x in b] if dot<0 else b
    return normalized(linear_blend(a,signed_b,corrected))

def bone_rotation_blend(a,b,weight):
    """Regular bone rotation helper's actual branch regimes."""
    a=list(map(F,a));b=list(map(F,b));dot=add(add(mul(a[0],b[0]),mul(a[2],b[2])),add(mul(a[1],b[1]),mul(a[3],b[3])))
    if abs(abs(dot)-1)<=F(2**-23):return a
    if dot<F(.9893559813499451):
        aligned_b=[-x for x in b] if dot<0 else b
        return polynomial_quaternion_blend(a,aligned_b,weight)
    return normalized(linear_blend(a,b,weight))

def additive_translation(base,delta,weight):
    return [add(a,mul(weight,b)) for a,b in zip(base,delta)]

def additive_rotation(base,delta,weight):
    weighted=polynomial_quaternion_blend([0,0,0,1],delta,weight)
    return quaternion_product(base,weighted)

def displacement_rotation_blend(a,b,weight):
    """Graph displacement helper uses a different exact-trigonometric branch."""
    dot=sum(x*y for x,y in zip(a,b));t=weight
    if dot<=-1 or dot>=1:return list(b)
    if dot>=F(.989355742931366):return normalized(linear_blend(a,b,t))
    theta=math.acos(abs(dot))
    if abs(theta)<=1e-6:return list(b)
    sign=-1 if dot<0 else 1
    s=math.sin(theta)
    return normalized([math.sin((1-t)*theta)/s*x+sign*math.sin(t*theta)/s*y for x,y in zip(a,b)])

def positive_phase_delta(start,end):
    delta=sub(end,start);crossed=delta<0
    while delta<0:delta=add(delta,1)
    return delta,crossed

def wrap_phase_inclusive(phase,lower=0.,upper=1.):
    """Both exact endpoints survive; this differs from a conventional modulo."""
    phase,lower,upper=map(F,(phase,lower,upper));span=F(max(0,sub(upper,lower)))
    if abs(span)<=EPS:return lower
    if phase<lower or upper<phase:
        remainder=F(math.fmod(sub(phase,lower),span))
        return add(upper if phase<lower else lower,remainder)
    return phase

def clip_time_interval(animation_length,start_phase,phase_delta):
    start=mul(animation_length,start_phase)
    return start,add(start,mul(animation_length,phase_delta))

def masked_channel_weight(mask_byte,global_weight):
    if not 0<=mask_byte<=255:raise ValueError('Mask byte must be 0..255')
    return mul(mul(mask_byte,F(1/255)),global_weight)

def examples():
    q=[0,0,math.sin(math.pi/4),math.cos(math.pi/4)]
    result={'normalized_weights':normalize_weights([-2,2,6]),'all_zero_weights':normalize_weights([0,0,0]),
            'incremental_schedule':incremental_blend_schedule([.25,.5,.25]),
            'axial_between_knots':axial_blend(3,[0,2,6]),'axial_endpoint':axial_blend(-5,[0,2,6]),
            'regular_rotation':bone_rotation_blend([0,0,0,1],q,.25),
            'additive_translation':additive_translation([1,2,3,0],[2,-1,0,0],.25),
            'additive_rotation':additive_rotation([0,0,0,1],q,.25),
            'linear_translation':linear_blend([0,0,0,0],[4,2,-2,0],.25),
            'phase_wrap_interval':positive_phase_delta(.9,.1),
            'exact_phase_endpoint':wrap_phase_inclusive(1),
            'clip_time_interval':clip_time_interval(2.5,.2,.3)}
    assert result['normalized_weights']==([0.,.25,.75],2)
    assert result['axial_between_knots']==(1,2,.25)
    assert result['axial_endpoint']==(0,0,None)
    assert incremental_blend_schedule([0,EPS])==[]
    return result
if __name__=='__main__':print(json.dumps(examples(),indent=2))
