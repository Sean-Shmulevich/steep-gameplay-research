"""Producer shape descriptors; LINK_SOLVER.md, Box and triangle descriptors."""
import math
from reference.central_impulse import f32

BOX_FACES = [(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(2,1,0,3),(7,4,5,6)]
BOX_EDGES = [(4,0,3,0),(5,1,0,1),(6,2,1,2),(7,3,2,3),
             (4,5,0,5),(5,6,1,5),(6,7,2,5),(7,4,3,5),
             (0,1,0,4),(1,2,1,4),(2,3,2,4),(3,0,3,4)]


def box_contact_shape(extents):
    """Construct the producer's signed corners, face planes and adjacency."""
    x,y,z = map(f32,extents)
    return dict(vertices=[[x,-y,z],[x,-y,-z],[-x,-y,-z],[-x,-y,z],
                          [x,y,z],[x,y,-z],[-x,y,-z],[-x,y,z]],
                planes=[[1,0,0,x],[0,0,-1,z],[-1,0,0,x],
                        [0,0,1,z],[0,-1,0,y],[0,1,0,y]],
                face_indices=list(BOX_FACES),edges=list(BOX_EDGES))


def triangle_contact_shape(first, second, third):
    """Construct opposing planes with native float32 normalization/dot order."""
    a,b,c = [list(map(f32,v)) for v in (first,second,third)]
    u=[f32(v-w) for v,w in zip(b,a)];v=[f32(v-w) for v,w in zip(c,a)]
    n=[f32(f32(u[1]*v[2])-f32(v[1]*u[2])),
       f32(f32(v[0]*u[2])-f32(u[0]*v[2])),
       f32(f32(u[0]*v[1])-f32(v[0]*u[1]))]
    squares=[f32(x*x) for x in n]
    length=f32(math.sqrt(f32(f32(squares[1]+squares[0])+squares[2])))
    if not length>0 or not math.isfinite(length):
        raise ValueError('Finite nondegenerate triangle required')
    inv=f32(1./length);n=[f32(x*inv) for x in n];opposite=[-x for x in n]
    def scalar(normal):
        p=[f32(x*y) for x,y in zip(normal,a)]
        return f32(f32(p[1]+p[0])+p[2])
    return dict(vertices=[a,b,c],planes=[n+[scalar(n)],opposite+[scalar(opposite)]],
                face_indices=[(0,1,2),(2,1,0)],edges=[(0,1,0,1),(1,2,0,1),(2,0,0,1)])
