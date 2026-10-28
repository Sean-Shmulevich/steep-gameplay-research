"""Box/triangle contact producer; LINK_SOLVER.md, Connected box-triangle producer."""
from .pose_contact_shapes import box_contact_shape, triangle_contact_shape
from .pose_contact_axis_selection import select_geometry_contact_axis
from .pose_contact_face_emit import emit_face_contacts
from .pose_contact_edge_emit import emit_edge_contact


def emit_box_triangle_contacts(output, capacity, extents, box_frame, triangle,
                               reduce_to_four=False, edge_enabled=True):
    """Emit native-layout records from box extents/frame and world triangle XYZ.

    All geometry-helper finite/nondegenerate domains apply. No runtime TLS or
    original allocator dependency is represented by this independent interface.
    """
    if capacity < 0 or len(output) < capacity*48:
        raise ValueError('Complete output storage for nonnegative capacity required')
    box = box_contact_shape(extents)
    tri = triangle_contact_shape(*triangle)
    identity = [[1,0,0],[0,1,0],[0,0,1],[0,0,0]]
    selection = select_geometry_contact_axis(box_frame, box, identity, tri,
                                              edge_enabled=edge_enabled)
    kind = selection['kind']
    if kind == 2:
        return emit_edge_contact(output, capacity, box_frame, box, identity, tri, selection)
    if kind == 0:
        return emit_face_contacts(output, capacity, box_frame, box, identity, tri,
                                  selection['first'], reduce_to_four, False)
    if kind == 1:
        return emit_face_contacts(output, capacity, identity, tri, box_frame, box,
                                  selection['second'], reduce_to_four, True)
    return 0
