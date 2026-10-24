"""Physical-body branch of snow frame publication.

Evidence: CENTRAL_IMPULSE.md, Physical-body decay frame producer. Runtime mode
selection, body identity/lifetime and the cached-basis fallback remain external.
"""
from .snow_post_pending import four
from reference.transform_inverse import inverse_transform
from reference.central_impulse import f32


def physical_body_decay_frames(body_transform, reciprocal_seed):
    """Publish basis/translation lanes then apply the recovered full inverse.

    Four native body vectors supply XYZ; stored W lanes are ignored. This is
    selected only when the native physical-body branch is known to apply.
    The explicit reciprocal seed retains inverse_transform's numerical contract.
    No orthonormality assumption, transpose shortcut or singular repair is added.
    """
    if len(body_transform) != 4:
        raise ValueError('Four native body vectors required')
    forward=[four(row) for row in body_transform]
    for i,row in enumerate(forward):
        row[3]=1.0 if i == 3 else 0.0
    inverse=inverse_transform(forward,reciprocal_seed)
    return dict(from_frame=forward[:3],to_frame=inverse[:3],
                forward_transform=forward,inverse_transform=inverse)


def cached_decay_frames(cached_basis, center_of_mass, direction, offset, reciprocal_seed):
    """Cached-basis branch after its native configuration validity gate.

    Input order follows runtime cache slots b40/b50/b60; publication reorders
    them as [2,0,1]. Basis W lanes are retained, not repaired. Translation XYZ is
    COM - offset*direction; W is forced to 1. Inputs must belong to one valid
    snapshot. Cache production, protected validity paths and mode selection are
    external. Evidence: CENTRAL_IMPULSE.md, Cached decay frame publication.
    """
    if len(cached_basis) != 3:
        raise ValueError('Three cached basis vectors required')
    cache=[four(row) for row in cached_basis]
    center=four(center_of_mass);direction=four(direction);offset=f32(offset)
    translation=[f32(center[i]-f32(offset*direction[i])) for i in range(3)]+[1.0]
    forward=[cache[2],cache[0],cache[1],translation]
    inverse=inverse_transform(forward,reciprocal_seed)
    return dict(from_frame=forward[:3],to_frame=inverse[:3],
                forward_transform=forward,inverse_transform=inverse)
