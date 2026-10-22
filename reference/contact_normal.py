"""Eligible contact-normal accumulation and normalization arithmetic.

CENTRAL_IMPULSE.md, 'Contact normal aggregation'. The reciprocal-square-root
instruction seed is an explicit dependency, not silently replaced by sqrt.
Candidate fitting, hemisphere selection and smoothing are outside this module.
"""
from reference.central_impulse import f32


def accumulate(contacts):
    total=[0.,0.,0.,0.]
    count=0
    for contact in contacts:
        if not contact['eligible']:
            continue
        weight=f32(contact['weight'])
        normal=tuple(map(f32,contact['normal']))
        if len(normal)!=4:
            raise ValueError('Four normal lanes required')
        total=[f32(a+f32(weight*b)) for a,b in zip(total,normal)]
        count+=1
    return {'weighted_normal':tuple(total),'eligible_count':count}


def normalize(weighted_normal, *, reciprocal_sqrt):
    v=tuple(map(f32,weighted_normal))
    if len(v)!=4:
        raise ValueError('Four weighted normal lanes required')
    squares=[f32(x*x) for x in v[:3]]
    squared=f32(squares[0]+f32(squares[1]+squares[2]))
    if squared<=0:
        raise ValueError('Degenerate normal requires caller handling; native exceptional path not reconstructed')
    seed=f32(reciprocal_sqrt(squared))
    correction=f32(f32(3)-f32(f32(seed*squared)*seed))
    scale=f32(correction*f32(f32(.5)*seed))
    return tuple(f32(x*scale) for x in v[:3])+(0.,)


def select_candidate(weighted, fitted, previous, *, had_previous_contact, reciprocal_sqrt):
    """Select between supplied normalized XYZ candidates; fitting is external.

    A previous-contact gate controls comparison. Ties select the fitted candidate.
    Low-Z poorly aligned fits have XYZ negated, Z replaced by .01, then normalize.
    """
    vectors=[]
    for vector in (weighted,fitted,previous):
        if len(vector)!=3:
            raise ValueError('Three candidate components required')
        vectors.append(tuple(map(f32,vector)))
    weighted,fitted,previous=vectors
    if not had_previous_contact:
        return {'normal':weighted+(0.,),'source':'weighted','fit_corrected':False}
    def dot(a,b):
        products=[f32(x*y) for x,y in zip(a,b)]
        return f32(products[0]+f32(products[1]+products[2]))
    weighted_dot=dot(weighted,previous)
    fit_dot=dot(fitted,previous)
    corrected=fitted[2]<f32(.1) and fit_dot<f32(.9)
    if corrected:
        fitted=normalize((-fitted[0],-fitted[1],f32(.01),0.),
                         reciprocal_sqrt=reciprocal_sqrt)[:3]
        fit_dot=dot(fitted,previous)
    use_fit=weighted_dot<=fit_dot
    return {'normal':(fitted+(-0. if corrected else 0.,)) if use_fit else weighted+(0.,),
            'source':'fitted' if use_fit else 'weighted','fit_corrected':corrected}


def smoothing_gain(previous_z, candidate_z, elapsed_dt, *, decay_lookup):
    """Temporary angular interpolation gain, reset on every invocation.

    Only called after the outer smoothing gates; it does not implement them.
    """
    from reference.input_cooker import cook
    previous_z,candidate_z=map(f32,(previous_z,candidate_z))
    base_rate=1. if previous_z<f32(.15) and candidate_z>f32(.3) else 60.
    result=cook(f32(.0001),f32(.75),elapsed_dt,
                {'baseDampFactorToZero':0.,'proportionalDampFactorToZero':0.,
                 'baseDampFactorToOne':base_rate,'proportionalDampFactorToOne':0.},
                decay_lookup=decay_lookup,epsilon=f32(.0001))
    return {'base_rate':base_rate,**result}


def rotate_normal(previous, quaternion, *, reciprocal_sqrt):
    """Recovered four-lane quaternion application and XYZ normalization.

    Previous normal has XYZ components; quaternion is XYZW. The native multiply uses
    (2, 2, 2, 0), preserving the sign of zero in W. Do not replace this with a
    generic rotation helper that rearranges the float32 operations.
    """
    if len(previous)!=3 or len(quaternion)!=4:
        raise ValueError('XYZ previous normal and XYZW quaternion required')
    v=tuple(map(f32,previous))+(0.,)
    q=tuple(map(f32,quaternion))
    p=[f32(q[i]*v[i]) for i in range(3)]
    dot=f32(p[0]+f32(p[1]+p[2]))
    cross=tuple(f32(f32(q[j]*v[k])-f32(v[j]*q[k]))
                for j,k in ((1,2),(2,0),(0,1)))+(0.,)
    squared_w=f32(q[3]*q[3])
    factor=f32(squared_w-f32(.5))
    rotated=tuple(f32(f32(f32(f32(c*q[3])+f32(dot*qi))+f32(factor*vi))*multiplier)
                  for c,qi,vi,multiplier in zip(cross,q,v,(2.,2.,2.,0.)))
    squares=[f32(x*x) for x in rotated[:3]]
    squared=f32(squares[0]+f32(squares[1]+squares[2]))
    if squared<=0:
        raise ValueError('Degenerate rotated normal requires caller handling')
    seed=f32(reciprocal_sqrt(squared))
    scale=f32(f32(f32(3)-f32(f32(seed*squared)*seed))*f32(seed*f32(.5)))
    return tuple(f32(scale*x) for x in rotated)


def smooth_normal(previous, candidate, control, elapsed_dt, *, angle_lookup,
                  decay_lookup, sine, cosine, reciprocal_sqrt):
    """Composed recovered smoothing block with explicit numerical services.

    Candidate generation and control-state production are caller dependencies.
    Callback implementations are not implicitly claimed to match native routines.
    """
    import math
    if len(previous)!=3 or len(candidate)!=3:
        raise ValueError('XYZ previous and candidate normals required')
    old=tuple(map(f32,previous));new=tuple(map(f32,candidate))
    output={'normal':new+(0.,),'branch':'control_bypass','gain':None,'quaternion':None}
    if f32(control)<=f32(.2):return output
    axis=tuple(f32(f32(old[j]*new[k])-f32(new[j]*old[k]))
               for j,k in ((1,2),(2,0),(0,1)))
    output['axis']=axis
    if all(abs(x)<=f32(.00001) for x in axis):
        output['branch']='axis_bypass';return output
    squares=[f32(x*x) for x in axis]
    length=f32(math.sqrt(f32(squares[0]+f32(squares[1]+squares[2]))))
    angle=f32(angle_lookup(length));output['angle']=angle
    if angle==0:
        output['branch']='angle_bypass';return output
    gain=smoothing_gain(old[2],new[2],elapsed_dt,decay_lookup=decay_lookup)
    half=f32(f32(gain['value']*angle)*f32(.5))
    sin_value=f32(sine(half));cos_value=f32(cosine(half))
    # Native quaternion construction has a length guard separate from per-lane axis gate.
    if length<=f32(.00001):
        quaternion=(0.,0.,0.,1.)
    else:
        scale=f32(sin_value/length)
        quaternion=tuple(f32(scale*x) for x in axis)+(cos_value,)
    output.update(normal=rotate_normal(old,quaternion,reciprocal_sqrt=reciprocal_sqrt),
                  branch='rotated',gain=gain,quaternion=quaternion,half_angle=half)
    return output
