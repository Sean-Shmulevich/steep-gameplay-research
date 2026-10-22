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
