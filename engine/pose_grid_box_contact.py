"""Terrain/box caller; LINK_SOLVER.md, Connected terrain-box contact caller."""
import struct
from reference.central_impulse import f32
from .pose_grid_contact_frames import grid_contact_frames
from .pose_box_resource_bounds import box_resource_bounds
from .pose_grid_height_contact import query_sampled_grid_contact
from .pose_grid_candidates import collect_grid_triangle_candidates
from .pose_grid_profile_gate import grid_triangle_profile_gate
from .pose_grid_cell import grid_triangle_vertices
from .pose_box_triangle_contact import emit_box_triangle_contacts
from .pose_grid_contact_records import convert_grid_contact_records
from .pose_grid_contact_filter import filter_grid_records


def emit_grid_box_contacts(output, capacity, resource, samples, terrain_frame,
                           box_frame, extents, terrain_profiles, box_profile, *,
                           profiles, preliminary=False, edge_enabled=True,
                           filter_enabled=True):
    """Compose kind3 box terrain caller; Python owns temporary candidate storage.

    preliminary also controls face-point reduction, as native descriptor byte90
    does. Samples/profile identities are supplied. Helper domains remain required.
    """
    if capacity<0 or len(output)<capacity*48:
        raise ValueError('Complete output storage required')
    inverse,relative=grid_contact_frames(terrain_frame,box_frame)
    query=box_resource_bounds(extents,relative)
    if preliminary:
        center=[f32(f32(query[j+3]+query[j])*f32(.5)) for j in range(3)]
        x,y,z=map(f32,extents)
        minimum=y if f32(z-y)>=0 else z
        radius=x if f32(minimum-x)>=0 else minimum
        if query_sampled_grid_contact(resource,samples,terrain_frame,center,radius,
                                      output if capacity else None):
            return 1
    candidates=collect_grid_triangle_candidates(resource,query)['ids']
    total=0
    f=[list(map(f32,row)) for row in terrain_frame]
    def world(v):
        return [f32(f32(f32(f32(f[0][j]*v[0])+f[3][j])+f32(f[1][j]*v[1]))
                    +f32(f[2][j]*v[2])) for j in range(3)]
    for triangle in candidates:
        _,admitted=grid_triangle_profile_gate(terrain_profiles,box_profile,triangle,profiles=profiles)
        if not admitted:continue
        vertices=[world(v) for v in grid_triangle_vertices(resource,samples,triangle)]
        batch=memoryview(output)[total*48:]
        count=emit_box_triangle_contacts(batch,capacity-total,extents,box_frame,vertices,
                                         preliminary,edge_enabled)
        convert_grid_contact_records(batch,0,count,triangle)
        if filter_enabled and struct.unpack_from('<I',resource,0x40)[0]==2:
            count=filter_grid_records(resource,samples,inverse,triangle,batch,count)
        total+=count
        if total==capacity:break
    return total


def emit_box_grid_contacts(output, capacity, resource, samples, box_frame,
                           terrain_frame, extents, terrain_profiles, box_profile, *,
                           profiles, preliminary=False, edge_enabled=True,
                           filter_enabled=True):
    """Reverse-order adapter with native post-return role reversal.

    One backing record is required even at capacity0: preliminary success can
    return1 and the adapter then reverses that retained record without production.
    """
    from .pose_contact_reverse import reverse_contact_records
    if len(output)<max(1,capacity)*48:
        raise ValueError('Backing storage for at least one retained record required')
    count=emit_grid_box_contacts(output,capacity,resource,samples,terrain_frame,
        box_frame,extents,terrain_profiles,box_profile,profiles=profiles,
        preliminary=preliminary,edge_enabled=edge_enabled,filter_enabled=filter_enabled)
    reverse_contact_records(output,0,count)
    return count
