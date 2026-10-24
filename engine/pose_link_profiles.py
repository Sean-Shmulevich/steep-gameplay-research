"""Recovered paired-body profile lookup for one link builder family.

Evidence: LINK_SOLVER.md, Paired link profile resolution.
"""
import struct


def resolve_pose_link_profiles(first_body,second_body,payload,*,resources):
    """Resolve opaque profile tokens through retained entry/resource tables.

    Bodies expose entries of resource tokens. Resources contain kind28, default20,
    optional map60/table50 and mapb0/tablea0. None means absent map; an empty
    present map is not a fallback. Tables and byte maps remain caller-owned.
    """
    first_index,second_index=struct.unpack_from('<HH',payload,0x48)
    first_resource=resources[first_body['entries'][first_index]]
    second_resource=resources[second_body['entries'][second_index]]
    detail=struct.unpack_from('<I',payload,0x3c)[0]
    short=struct.unpack_from('<H',payload,0x3e)[0]
    def resolve(resource):
        kind=resource['kind28']&0x7fff
        if kind==6 and resource['map60'] is not None:
            return resource['table50'][resource['map60'][short]]
        if kind==7 and resource['mapb0'] is not None:
            return resource['tablea0'][resource['mapb0'][detail>>1]]
        return resource['default20']
    return resolve(first_resource),resolve(second_resource)
