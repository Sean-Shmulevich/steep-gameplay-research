"""Recovered tetrahedral contact evaluator, separate from the point controller.

Caller supplies geometry and profile selection explicitly. This does not infer
face areas or solve multiple simultaneous contacts. All body vectors use Z-up.
"""
from reference import snow
from .math3d import vector, normalize
from .assets import canonical

def evaluate_cell(body,world_vertices,surface,dt,settings):
    if len(world_vertices)!=4:raise ValueError('A tetrahedron requires four vertices')
    for point in world_vertices:vector(point)
    if not 0<dt<=.05:raise ValueError('Invalid cell timestep')
    normal=normalize(vector(surface['normal']));plane_point=vector(surface['point'])
    offset=-snow.dot(normal,plane_point);material=surface['material']
    volume,centroid=snow.clipped_tetra(world_vertices,normal,offset)
    if volume==0:return dict(submerged_volume=0.,pressure_impulse=[0.,0.,0.],contact_impulse=[0.,0.,0.],evidence='recovered local cell math')
    relative=snow.point_relative_velocity(body['velocity'],body['angular_velocity'],centroid,body['position'],surface.get('velocity',[0,0,0]))
    weight=settings['face_weight'];total=settings['total_weight']
    if total<=0 or weight<0 or body['mass']<=0:raise ValueError('Invalid contact weights/mass')
    result=snow.cell_step(world_vertices,normal,offset,material['thickness'],material['density'],settings['depth_curve'],settings.get('tilt_gain',1.),settings.get('speed_gain',1.),settings.get('gravity',-9.81),settings.get('pressure_activation',1.),dt,normalize(vector(settings['face_normal'])),weight,body['mass'],total,settings.get('contact_activation',1.),relative,material['normal_frequency'],material['tangent_frequency'],settings.get('surface_frequency',0.))
    result['point_velocity']=relative;result['evidence']='recovered cell math; caller-selected profiles and geometry'
    canonical(result);return result

def apply_result(body,result,inverse_world_inertia):
    if result['submerged_volume']==0:return
    if len(inverse_world_inertia)!=3:raise ValueError('3x3 inverse inertia required')
    for row in inverse_world_inertia:vector(row)
    impulse=snow.add(result['pressure_impulse'],result['contact_impulse'])
    velocity,omega=snow.apply_point_impulse(body['velocity'],body['angular_velocity'],impulse,result['centroid'],body['position'],body['mass'],inverse_world_inertia)
    canonical([velocity,omega]);body['velocity']=list(velocity);body['angular_velocity']=list(omega)
