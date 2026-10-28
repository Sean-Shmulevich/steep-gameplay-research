"""Grid record filtering; LINK_SOLVER.md, Complete grid record filter."""
import math
import struct
from reference.central_impulse import f32
from engine.pose_grid_cell import (grid_triangle_vertices,
    grid_triangle_sample_indices, grid_vertex_neighbors)
from engine.pose_grid_edge_filter import reject_grid_edge


def filter_grid_records(resource,samples,frame,triangle_id,records,count):
    """Filter retained 48-byte records in place; return the remaining count.

    Record XYZ direction is at0; XYZ position at16. Remaining bytes are opaque.
    Inputs must be finite/nondegenerate; initialized native XYZ masking assumed.
    Unused tail storage persists. This is not a contact-generation interface.
    """
    if not 0 <= count <= len(records)//48:
        raise ValueError('Complete retained record span required')
    if count==0:return 0
    def sub(a,b):return [f32(x-y) for x,y in zip(a,b)]
    def dot(a,b):
        p=[f32(x*y) for x,y in zip(a,b)]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.))
    def cross(a,b):
        return [f32(f32(a[1]*b[2])-f32(a[2]*b[1])),
                f32(f32(a[2]*b[0])-f32(a[0]*b[2])),
                f32(f32(a[0]*b[1])-f32(a[1]*b[0]))]
    def normalize(a):
        length=f32(math.sqrt(dot(a,a)))
        if not length>0:raise ValueError('Nondegenerate neighbor direction required')
        inv=f32(1./length)
        return [f32(x*inv) for x in a]
    vertices=[v[:3] for v in grid_triangle_vertices(resource,samples,triangle_id)]
    ids=grid_triangle_sample_indices(resource,triangle_id)
    a,b,c=vertices
    normal=cross(sub(b,a),sub(c,a));den=dot(normal,normal)
    if not den>0:raise ValueError('Nondegenerate triangle required')
    reciprocal=f32(1./den)
    upper=f32(.9999);lower=f32(.0001);t=f32(.00001)
    frame=[list(map(f32,row)) for row in frame]
    if len(frame)!=4 or any(len(row)!=3 for row in frame):
        raise ValueError('Four XYZ transform rows required')
    i=0
    while i<count:
        raw_d=struct.unpack_from('<3f',records,i*48)
        raw_p=struct.unpack_from('<3f',records,i*48+16)
        p=[f32(f32(f32(f32(frame[0][j]*raw_p[0])+frame[3][j])+
                      f32(frame[1][j]*raw_p[1]))+f32(frame[2][j]*raw_p[2])) for j in range(3)]
        d=[f32(f32(f32(frame[1][j]*raw_d[1])+f32(frame[0][j]*raw_d[0]))+
                   f32(frame[2][j]*raw_d[2])) for j in range(3)]
        if not all(math.isfinite(x) for x in p+d):raise ValueError('Finite record transforms required')
        pa,pb,pc=[sub(v,p) for v in vertices]
        weights=[f32(dot(v,normal)*reciprocal) for v in
                 (cross(pb,pc),cross(pc,pa),cross(pa,pb))]
        reject=False;vertex=next((k for k in range(3) if weights[k]>upper),None)
        if vertex is not None:
            for neighbor in grid_vertex_neighbors(resource,samples,ids[vertex]):
                if dot(normalize(sub(neighbor,vertices[vertex])),d)>t:
                    reject=True;break
        else:
            edge=next(((x,y) for k,x,y in ((2,0,1),(0,1,2),(1,2,0)) if weights[k]<lower),None)
            if edge is not None:
                x,y=edge
                reject=reject_grid_edge(resource,samples,ids[x],ids[y],vertices[x],vertices[y],d,[t]*4)
        if reject:
            count-=1
            records[i*48:(i+1)*48]=records[count*48:(count+1)*48]
        else:i+=1
    return count
