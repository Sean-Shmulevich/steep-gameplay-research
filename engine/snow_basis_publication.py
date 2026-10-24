"""Recovered successful basis callback publication to the runtime pose record.

Evidence: CENTRAL_IMPULSE.md, Successful basis pose publication.
This stage does not overwrite the source cache or publish decay transforms.
"""
import math
from reference.central_impulse import f32
from .snow_post_pending import four


def publish_basis_pose(cached_basis, auxiliary_direction, frame_vector70,
                       runtime_vector940, reciprocal_sqrt_seed):
    """Return published fields from the already-accepted callback path.

    Normalize in source order 2,1,0 using four-lane norms, then store XYZ in
    source order 0,1,2. Other two copied vectors retain their supplied XYZ.
    """
    if len(cached_basis)!=3:raise ValueError('Three cached vectors required')
    cache=[four(v) for v in cached_basis]
    pose=[None,None,None]
    for index in (2,1,0):
        v=cache[index]
        squares=[f32(x*x) for x in v]
        n=f32(f32(squares[1]+squares[3])+f32(squares[0]+squares[2]))
        if not math.isfinite(n) or n<=0:raise ValueError('Finite positive four-lane norm required')
        seed=f32(reciprocal_sqrt_seed(n))
        if not math.isfinite(seed):raise ValueError('Finite rsqrt seed required')
        scale=f32(f32(3.-f32(f32(seed*n)*seed))*f32(.5*seed))
        pose[index]=[f32(scale*x) for x in v[:3]]
    return {'pose_basis_xyz':pose,'auxiliary_direction':four(auxiliary_direction),
            'frame_vector70_xyz':four(frame_vector70)[:3],
            'runtime_vector940_xyz':four(runtime_vector940)[:3]}
