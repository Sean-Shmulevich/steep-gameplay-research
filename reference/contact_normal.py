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
