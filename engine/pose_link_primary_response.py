"""Recovered primary link row response selection.

Evidence: CENTRAL_IMPULSE.md, Primary link row response selection.
"""
import math
from reference.central_impulse import f32


def link_primary_response(separation, normal, *, opposite_motion_projection,
                          response, combined40, offset1c, threshold20):
    """Combine signed separation and motion candidates using raw profile/context fields.

    Separation is second world point minus first world point. The supplied motion
    projection is dot(normal, negative first-body point motion), before tangent
    removal. Finite arithmetic only; no inferred bounce/penetration units.
    """
    if len(separation)!=3 or len(normal)!=3:raise ValueError('Three components required')
    values=[f32(x) for x in (*separation,*normal,opposite_motion_projection,
                            response,combined40,offset1c,threshold20)]
    if not all(math.isfinite(x) for x in values):raise ValueError('Finite inputs required')
    delta=values[:3];n=values[3:6];q,gain,factor,offset,threshold=values[6:]
    products=[f32(delta[i]*-n[i]) for i in range(3)]
    distance=f32(f32(products[0]+products[1])+f32(products[2]+0.0))
    position=f32(f32(distance+offset)*gain)
    admitted=f32(q-threshold)<0
    motion=f32(q*factor) if admitted else 0.0
    choose_motion=f32(abs(position)-abs(motion))<0
    return dict(response=motion if choose_motion else position,
                position_candidate=position,motion_candidate=motion,
                motion_admitted=admitted,motion_selected=choose_motion)
