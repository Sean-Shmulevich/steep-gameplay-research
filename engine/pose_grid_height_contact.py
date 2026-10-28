"""Below-height contact branch; LINK_SOLVER.md, Preliminary height contact."""
import struct
from reference.central_impulse import f32


def query_grid_height_contact(resource, frame, center, radius, output, *, height_query):
    """Use explicit height_query(resource,x,y)->(height,triangle_id) dependency.

    Return bool; output=None performs admission without writing a record.
    This recovers the wrapper only, not the height interpolation service.
    """
    center=list(map(f32,center));radius=f32(radius)
    height, triangle_id=height_query(resource,center[0],center[1])
    height=f32(height)
    if not center[2] <= height:
        return False
    f=[list(map(f32,row)) for row in frame]
    separation=f32(f32(center[2]-height)-radius)
    # Preserve native arithmetic including zero-component multiplication.
    local_normal=[0.,0.,1.]
    projected=[f32(center[j]-f32(separation*local_normal[j])) for j in range(3)]
    normal=[f32(f32(f32(f[1][j]*0.)+f32(f[0][j]*0.))+f32(f[2][j]*1.)) for j in range(3)]
    def point(v):
        return [f32(f32(f32(f32(f[0][j]*v[0])+f[3][j])+f32(f[1][j]*v[1]))
                    +f32(f[2][j]*v[2])) for j in range(3)]
    first,second=point(projected),point(center)
    if output is not None:
        if len(output)<48 or not 0<=triangle_id<2**32:
            raise ValueError('Complete record storage and uint32 triangle ID required')
        struct.pack_into('<4f3fI3fI',output,0,*normal,separation,*first,0,*second,triangle_id)
    return True
