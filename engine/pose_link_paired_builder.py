"""Paired128-byte contact rows; LINK_SOLVER.md, Connected paired single builder."""
import struct
from reference.central_impulse import f32
from .pose_link_profiles import resolve_pose_link_profiles
from .pose_link_coefficients import link_response_coefficients
from .pose_link_paired_motion import paired_link_point_motion,paired_link_tangent_basis
from .pose_link_primary_response import link_primary_response
from .pose_link_result_binding import bind_pose_link_results


def build_paired_pose_link_rows(context, first, second, payload, *, resources, profiles, modes):
    """Metadata-set/single family with retained128-byte primary/secondary rows.

    Context/body fields follow the single-family API, but row arrays and their
    native counters/layout are distinct. No allocator or solver is supplied here.
    """
    if len(payload)!=288:raise ValueError('Complete288-byte payload required')
    count=struct.unpack_from('<I',payload,0x110)[0]
    if count>4:raise ValueError('At most four retained payload rows required')
    tokens=resolve_pose_link_profiles(first,second,payload,resources=resources)
    coefficients=link_response_coefficients(*(profiles[t] for t in tokens),modes,
        context_scalar=context['scalar_c'],default_factor=context['factor14'],context_flags=context['flags38'])
    def vec(row,offset):return struct.unpack_from('<3f',row,offset)
    def cross(a,b):return [f32(f32(a[(i+1)%3]*b[(i+2)%3])-f32(b[(i+1)%3]*a[(i+2)%3])) for i in range(3)]
    def dot(a,b):
        p=[f32(x*y) for x,y in zip(a,b)]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.0))
    def store(row,offset,values):struct.pack_into('<4f',row,offset,*values)
    for i in range(count):
        start=0x10+64*i;record=bytearray(payload[start:start+64])
        normal,p1,p2=vec(record,0),vec(record,16),vec(record,32)
        primary=context['primary_rows'][context['primary_count']]
        context['primary_count']=(context['primary_count']+1)&0xffffffff
        secondary=[]
        for _ in range(2):
            secondary.append(context['secondary_rows'][context['secondary_count']])
            context['secondary_count']=(context['secondary_count']+1)&0xffffffff
        rows=[primary,*secondary]
        if any(len(row)!=128 for row in rows):raise ValueError('Complete128-byte rows required')
        indices=bind_pose_link_results(context,record,rows)
        motion=paired_link_point_motion(first,second,p1,p2)
        tangent=paired_link_tangent_basis(motion['relative_motion'],normal)
        arm1=motion['first']['arm'];arm2=motion['second']['arm']
        world1=[f32(motion['first']['center_world'][j]+arm1[j]) for j in range(3)]
        world2=[f32(arm2[j]+motion['second']['center_world'][j]) for j in range(3)]
        delta=[f32(world2[j]-world1[j]) for j in range(3)]
        for row,direction,lane in zip(secondary,(tangent['first'],tangent['second']),(tangent['first_lane3'],0.0)):
            zero=f32(dot(delta,direction)*0.0)
            store(row,16,[zero,zero,zero,f32(3.4028234663852886e38)])
            store(row,32,[*direction,lane]);store(row,48,[*cross(arm1,direction),0.0])
            store(row,80,[*cross(direction,arm2),0.0])
            struct.pack_into('<I',row,96,indices[0]);store(row,112,[coefficients['combined30']]*4)
        if coefficients['seed_gate']==0.0:
            result=context['result_rows'][indices[0]]
            if len(result)!=16:raise ValueError('Complete16-byte result row required')
            result[:]=record[48:52]*4
        response=link_primary_response(delta,normal,opposite_motion_projection=tangent['relative_motion_projection'],
            response=coefficients['response'],combined40=coefficients['combined40'],
            offset1c=context['field1c'],threshold20=context['field20'])
        direction=[-x for x in normal];half=[f32(v*.5) for v in delta]
        lever1=[f32(half[j]+arm1[j]) for j in range(3)]
        lever2=[f32(arm2[j]-half[j]) for j in range(3)]
        store(primary,16,[response['response']]*4);store(primary,32,[*direction,-0.0])
        store(primary,48,[*cross(lever1,direction),0.0]);struct.pack_into('<Q',primary,80,0)
        store(primary,96,[coefficients['seed_gate']]*4)
        store(primary,112,[*cross(direction,lever2),0.0])
        for row in rows:struct.pack_into('<HH',row,0,first['index1c'],second['index1c'])
        payload[start:start+64]=record
