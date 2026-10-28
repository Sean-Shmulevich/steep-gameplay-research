"""Metadata-set paired multi-contact builder; LINK_SOLVER.md, Connected paired multi builder."""
import struct
from reference.central_impulse import f32
from engine.pose_link_profiles import resolve_pose_link_profiles
from engine.pose_link_coefficients import link_response_coefficients
from engine.pose_link_paired_motion import paired_link_point_motion,paired_link_tangent_basis
from engine.pose_link_primary_response import link_primary_response
from engine.pose_link_patch_geometry import contact_patch_geometry,contact_patch_basis


def build_paired_multi_pose_link_rows(context,first,second,payload,*,resources,profiles,modes):
    """Retained128-byte primary and256-byte shared rows with arena-relative links.

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
    if len(shared)!=256:raise ValueError('Complete256-byte shared row required')
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
        if len(row)!=128:raise ValueError('Complete128-byte primary row required')
        context['primary_count']=(pi+1)&0xffffffff
        ri=context['result_count'];context['result_count']=(ri+1)&0xffffffff
        struct.pack_into('<HHI',row,0,first['index1c'],second['index1c'],ri)
        struct.pack_into('<I',payload,start+0x34,ri)
        cached=bytes(payload[start+0x30:start+0x34]);value=struct.unpack('<f',cached)[0]
        total=f32(total+value)
        if co['seed_gate']==0:context['result_rows'][ri][:]=cached*4
        motion=paired_link_point_motion(first,second,p1,p2)
        tangent=paired_link_tangent_basis(motion['relative_motion'],normal)
        arm=motion['first']['arm'];arm2=motion['second']['arm']
        world1=[f32(motion['first']['center_world'][j]+arm[j]) for j in range(3)]
        world2=[f32(arm2[j]+motion['second']['center_world'][j]) for j in range(3)]
        delta=[f32(world2[j]-world1[j]) for j in range(3)]
        response=link_primary_response(delta,normal,opposite_motion_projection=tangent['relative_motion_projection'],response=co['response'],combined40=co['combined40'],offset1c=context['field1c'],threshold20=context['field20'])
        direction=[-x for x in normal];lever=[f32(f32(.5*delta[j])+arm[j]) for j in range(3)]
        store(row,0x10,[response['response']]*4);store(row,0x20,[*direction,-0.0])
        store(row,0x30,[*cross(lever,direction),0.0]);store(row,0x60,[co['seed_gate']]*4)
        lever2=[f32(arm2[j]-f32(.5*delta[j])) for j in range(3)]
        store(row,0x70,[*cross(direction,lever2),0.0])
        relative=(context['shared_base']+256*si+0xe0)-(context['primary_base']+128*pi)
        if relative%16:raise ValueError('Arena row bases must align to16 bytes')
        struct.pack_into('<q',row,0x50,relative>>4)
        arms.append([f32(p1[j]-f32(first['offset128'][j])) for j in range(3)])
    patch=contact_patch_geometry(first['frame']['basis'],motion['first']['center_world'],arms)
    arm1=patch['centroid_arm']
    arm2=[f32(patch['centroid_world'][j]-motion['second']['center_world'][j]) for j in range(3)]
    velocities=[]
    for body,arm in ((first,arm1),(second,arm2)):
        angular=[f32(v) for v in body['motion1ac']]
        spin=cross(angular,arm)
        velocities.append([f32(spin[j]+f32(body['motion1a0'][j])) for j in range(3)])
    relative=[f32(velocities[0][j]-velocities[1][j]) for j in range(3)]
    basis=contact_patch_basis(vec(0x10),arm1,relative,[0.,0.,0.],patch['spread'])
    # Separate transpose for each body's angular columns; second has opposite signs.
    shared[0x10:0x20]=bytes(16)
    first_t=basis['first'];second_t=basis['second']
    a1=cross(arm1,first_t);b1=cross(arm1,second_t)
    a2=cross(arm2,[-x for x in first_t]);b2=cross(arm2,[-x for x in second_t])
    for j in range(3):
        store(shared,0x20+16*j,[first_t[j],second_t[j],0.,0.])
        store(shared,0x50+16*j,[a1[j],b1[j],basis['spread_direction'][j],0.])
        store(shared,0x80+16*j,[a2[j],b2[j],-basis['spread_direction'][j],0.])
    store(shared,0xe0,[total]*4);store(shared,0xf0,[co['combined30']]*4)
