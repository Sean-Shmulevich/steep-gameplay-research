"""Face separation query; LINK_SOLVER.md, Contact face-distance query."""
from reference.central_impulse import f32


def query_contact_faces(first_frame,first_shape,second_frame,second_shape):
    """Return distance and first-shape plane index for finite supplied geometry.

    Shapes expose planes [nx,ny,nz,d] and vertices [x,y,z]. No normalization or
    inverse-transpose substitution is made. Fourth frame lanes are assumed zero.
    Empty plane lists return (-FLT_MAX, UINT_MAX). Nonempty planes require vertices.
    """
    def dot(a,b):
        p=[f32(x*y) for x,y in zip(a,b)]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.))
    f,g=[[list(map(f32,row)) for row in frame] for frame in (first_frame,second_frame)]
    best=f32(-3.4028234663852886e38);selected=0xffffffff
    planes=first_shape['planes']
    if planes and not second_shape['vertices']:raise ValueError('Support vertices required')
    vertices=[list(map(f32,v)) for v in second_shape['vertices']]
    for i,plane in enumerate(planes):
        x,y,z,d=map(f32,plane)
        n=[f32(f32(f32(f[1][j]*y)+f32(f[0][j]*x))+f32(f[2][j]*z)) for j in range(3)]
        distance=f32(dot(f[3],n)+d)
        local=[dot([-q for q in n],g[j]) for j in range(3)]
        support=None;value=f32(-3.4028234663852886e38)
        for vertex in vertices:
            candidate=dot(vertex,local)
            if candidate>value:value=candidate;support=vertex
        if support is None:raise ValueError('Finite support above negative FLT_MAX required')
        world=[f32(f32(f32(f32(g[0][j]*support[0])+g[3][j])+
                        f32(g[1][j]*support[1]))+f32(g[2][j]*support[2])) for j in range(3)]
        separation=f32(dot(world,n)-distance)
        if separation>0:return separation,i
        if separation>best:best=separation;selected=i
    return best,selected
