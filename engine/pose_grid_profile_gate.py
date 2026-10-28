"""Terrain triangle admission; LINK_SOLVER.md, Terrain profile admission."""


def grid_triangle_profile_gate(resource, other_resource, triangle_id, *, profiles):
    """Return selected profile token and whether either directional mask overlaps.

    Resources supply default20 and terrain supplies optional mapb0/tablea0.
    Tokens are caller-owned identities; this API does not follow native pointers.
    """
    if type(triangle_id) is not int or not 0 <= triangle_id < 2**32:
        raise ValueError('uint32 triangle identifier required')
    mapping = resource['mapb0']
    if mapping is None:
        token = resource['default20']
    else:
        index = mapping[triangle_id >> 1]
        if type(index) is not int or not 0 <= index < 256:
            raise ValueError('Terrain map entry must be uint8')
        token = resource['tablea0'][index]
    terrain = profiles[token]
    other = profiles[other_resource['default20']]
    for profile in (terrain, other):
        for key in ('mask48', 'mask50'):
            value = profile[key]
            if type(value) is not int or not 0 <= value < 2**64:
                raise ValueError('Profile masks must be uint64')
    admitted = bool((terrain['mask50'] & other['mask48']) |
                    (other['mask50'] & terrain['mask48']))
    return token, admitted
