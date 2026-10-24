"""Physical-body branch of snow frame publication.

Evidence: CENTRAL_IMPULSE.md, Physical-body decay frame producer. Runtime mode
selection, body identity/lifetime and the cached-basis fallback remain external.
"""
from .snow_post_pending import four
from reference.transform_inverse import inverse_transform


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
