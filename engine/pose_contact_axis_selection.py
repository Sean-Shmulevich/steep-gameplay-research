"""Contact axis selection; LINK_SOLVER.md, Contact producer axis selection."""
from reference.central_impulse import f32


def select_contact_axis(first_frame,first_shape,second_frame,second_shape,*,
                        edge_enabled,face_query,edge_query):
    """Select kind/index pair/distance using explicit geometry services.

    face_query(frame,shape,other_frame,other_shape) returns distance,index.
    edge_query receives the same arguments plus mutable seed distance/first/second.
    Supported domain: finite distances; opaque shape/frame identities retained.
    """
    first,fi=face_query(first_frame,first_shape,second_frame,second_shape)
    first=f32(first)
    if first>0:return dict(kind=3,first=fi,second=0xffffffff,distance=first)
    second,si=face_query(second_frame,second_shape,first_frame,first_shape)
    second=f32(second)
    if second>0:return dict(kind=3,first=0xffffffff,second=si,distance=second)
    def biased(value):return f32(f32(value*f32(.98))+f32(.01))
    if edge_enabled:
        edge=dict(distance=f32(-3.4028234663852886e38),first=0xffffffff,second=0xffffffff)
        edge_query(first_frame,first_shape,second_frame,second_shape,edge)
        value=f32(edge['distance'])
        if value>biased(first) and value>biased(second):
            return dict(kind=2,first=edge['first'],second=edge['second'],distance=value)
    if first>biased(second):
        return dict(kind=0,first=fi,second=0xffffffff,distance=first)
    return dict(kind=1,first=0xffffffff,second=si,distance=second)
