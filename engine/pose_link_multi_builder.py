"""Metadata-clear multi-contact builder; LINK_SOLVER.md, Connected multi builder."""
import struct
from reference.central_impulse import f32
from engine.pose_link_profiles import resolve_pose_link_profiles
from engine.pose_link_coefficients import link_response_coefficients
from engine.pose_link_geometry import link_point_geometry
from engine.pose_link_tangents import link_tangent_basis
from engine.pose_link_primary_response import link_primary_response
from engine.pose_link_patch_geometry import contact_patch_geometry,contact_patch_basis,pack_contact_patch_directions


def build_multi_pose_link_rows(context,first,second,payload,*,resources,profiles,modes):
    """Retained112-byte primary and208-byte shared rows with arena-relative links.

    primary_base/shared_base are byte offsets in one abstract arena. They determine
    signed16-byte-unit links; they are not host pointers. No allocation is supplied.
    """
    if len(payload)!=288:raise ValueError('Complete288-byte payload required')
    count=struct.unpack_from('<I',payload,0x110)[0]
    if not 1<=count<=4:raise ValueError('One to four contacts required')
    tokens=resolve_pose_link_profiles(first,second,payload,resources=resources)
    co=link_response_coefficients(*(profiles[t] for t in tokens),modes,
        context_scalar=context['scalar_c'],default_factor=context['factor14'],context_flags=context['flags38'])
    si=context['shared_count'];shared=context['shared_rows'][si]
    if len(shared)!=208:raise ValueError('Complete208-byte shared row required')
    context['shared_count']=(si+1)&0xffffffff
    ri=context['result_count'];context['result_count']=(ri+1)&0xffffffff
    struct.pack_into('<HHI',shared,0,first['index1c'],second['index1c'],ri)
    def vec(o):return struct.unpack_from('<3f',payload,o)
    def cross(a,b):return [f32(f32(a[(j+1)%3]*b[(j+2)%3])-f32(a[(j+2)%3]*b[(j+1)%3])) for j in range(3)]
    def store(row,o,v):struct.pack_into('<4f',row,o,*v)
    total=0.;arms=[]
    for i in range(count):
        start=0x10+64*i;normal,p1,p2=vec(start),vec(start+16),vec(start+32)
        pi=context['primary_count'];row=context['primary_rows'][pi]
        if len(row)!=112:raise ValueError('Complete112-byte primary row required')
        context['primary_count']=(pi+1)&0xffffffff
        ri=context['result_count'];context['result_count']=(ri+1)&0xffffffff
        struct.pack_into('<HHI',row,0,first['index1c'],second['index1c'],ri)
        struct.pack_into('<I',payload,start+0x34,ri)
        cached=bytes(payload[start+0x30:start+0x34]);value=struct.unpack('<f',cached)[0]
        total=f32(total+value)
        if co['seed_gate']==0:context['result_rows'][ri][:]=cached*4
        geometry=link_point_geometry(first['frame'],second['frame'],p1,p2,first['offset128'])
        tangent=link_tangent_basis(first['frame']['basis'],p1,first['offset128'],first['motion1a0'],first['motion1ac'],normal)
        delta=geometry['separation'];arm=geometry['first_arm']
        response=link_primary_response(delta,normal,opposite_motion_projection=tangent['opposite_motion_projection'],response=co['response'],combined40=co['combined40'],offset1c=context['field1c'],threshold20=context['field20'])
        direction=[-x for x in normal];lever=[f32(f32(.5*delta[j])+arm[j]) for j in range(3)]
        store(row,0x10,[response['response']]*4);store(row,0x20,[*direction,-0.0])
        store(row,0x30,[*cross(lever,direction),0.0]);store(row,0x60,[co['seed_gate']]*4)
        relative=(context['shared_base']+208*si+0xb0)-(context['primary_base']+112*pi)
        if relative%16:raise ValueError('Arena row bases must align to16 bytes')
        struct.pack_into('<q',row,0x50,relative>>4)
        arms.append([f32(p1[j]-f32(first['offset128'][j])) for j in range(3)])
    patch=contact_patch_geometry(first['frame']['basis'],geometry['first_center_world'],arms)
    basis=contact_patch_basis(vec(0x10),patch['centroid_arm'],first['motion1a0'],first['motion1ac'],patch['spread'])
    pack_contact_patch_directions(shared,basis)
    store(shared,0xb0,[total]*4);store(shared,0xc0,[co['combined30']]*4)
