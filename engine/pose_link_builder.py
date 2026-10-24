"""Independent assembly of the recovered metadata-clear/single link builder.

Evidence: LINK_SOLVER.md, Connected single-family link row builder.
"""
import struct
from reference.central_impulse import f32
from engine.pose_link_profiles import resolve_pose_link_profiles
from engine.pose_link_coefficients import link_response_coefficients
from engine.pose_link_geometry import link_point_geometry
from engine.pose_link_tangents import link_tangent_basis
from engine.pose_link_primary_response import link_primary_response
from engine.pose_link_result_binding import bind_pose_link_results,seed_pose_link_result


def build_pose_link_rows(context, first, second, payload, *, resources, profiles, modes):
    """Build into retained 112-byte row arrays and 16-byte result storage.

    Context supplies primary_count/rows, secondary_count/rows, result_count/rows,
    flags38, scalar_c, factor14, field1c and field20. Bodies supply frame,
    offset128, motion1a0/1ac, index1c and entries. Only first body uses motion and
    offset fields. No allocation, capacity repair or exceptional arithmetic model.
    """
    if len(payload)!=288:raise ValueError('Complete 288-byte payload required')
    count=struct.unpack_from('<I',payload,0x110)[0]
    if count>4:raise ValueError('At most four retained payload rows required')
    tokens=resolve_pose_link_profiles(first,second,payload,resources=resources)
    coefficients=link_response_coefficients(*(profiles[t] for t in tokens),modes,
        context_scalar=context['scalar_c'],default_factor=context['factor14'],context_flags=context['flags38'])
    def vec(row,offset):return struct.unpack_from('<3f',row,offset)
    def cross(a,b):
        return [f32(f32(a[(i+1)%3]*b[(i+2)%3])-f32(a[(i+2)%3]*b[(i+1)%3])) for i in range(3)]
    def dot(a,b):
        p=[f32(x*y) for x,y in zip(a,b)]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.0))
    def store(row,offset,values):struct.pack_into('<4f',row,offset,*values)
    for i in range(count):
        start=0x10+64*i;record=bytearray(payload[start:start+64])
        normal,p1,p2=vec(record,0),vec(record,0x10),vec(record,0x20)
        primary=context['primary_rows'][context['primary_count']]
        context['primary_count']=(context['primary_count']+1)&0xffffffff
        secondary=[]
        for _ in range(2):
            secondary.append(context['secondary_rows'][context['secondary_count']])
            context['secondary_count']=(context['secondary_count']+1)&0xffffffff
        rows=[primary,*secondary]
        if any(len(r)!=112 for r in rows):raise ValueError('Complete retained 112-byte solver rows required')
        indices=bind_pose_link_results(context,record,rows)
        geometry=link_point_geometry(first['frame'],second['frame'],p1,p2,first['offset128'])
        tangent=link_tangent_basis(first['frame']['basis'],p1,first['offset128'],first['motion1a0'],first['motion1ac'],normal)
        delta=geometry['separation'];arm=geometry['first_arm']
        for row,direction,lane3 in zip(secondary,(tangent['first'],tangent['second']),(tangent['first_lane3'],0.0)):
            zero=f32(dot(delta,direction)*0.0)
            store(row,0x10,[zero,zero,zero,f32(3.4028234663852886e38)])
            store(row,0x20,[*direction,lane3])
            store(row,0x30,[*cross(arm,direction),0.0])
            store(row,0x60,[coefficients['combined30']]*4)
            struct.pack_into('<I',row,0x50,indices[0])
        gate_bits=struct.unpack('<I',struct.pack('<f',coefficients['seed_gate']))[0]
        seed_pose_link_result(context,record,secondary[1],primary_index=indices[0],gate_bits=gate_bits)
        response=link_primary_response(delta,normal,opposite_motion_projection=tangent['opposite_motion_projection'],
            response=coefficients['response'],combined40=coefficients['combined40'],
            offset1c=context['field1c'],threshold20=context['field20'])
        direction=[-x for x in normal]
        lever=[f32(f32(0.5*delta[j])+arm[j]) for j in range(3)]
        store(primary,0x10,[response['response']]*4)
        store(primary,0x20,[*direction,-0.0])
        store(primary,0x30,[*cross(lever,direction),0.0])
        store(primary,0x60,[coefficients['seed_gate']]*4)
        struct.pack_into('<Q',primary,0x50,0)
        for row in rows:struct.pack_into('<HH',row,0,first['index1c'],second['index1c'])
        payload[start:start+64]=record
