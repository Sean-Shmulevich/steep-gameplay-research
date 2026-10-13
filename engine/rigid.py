"""Optional synthetic rigid hull with recovered tetrahedral snow kernels.

This is an independent integration mode, not the complete original constraint
solver. Six tetrahedra represent an invented box. Volume weights stand in for
unrecovered face/contact selection. Steering, jump and substrate are designed.
Angular momentum is stored in world space; inertia rotates with the body.
"""
import copy
import math
from reference import snow,skeleton
from .contact import evaluate_cell
from .math3d import vector,normalize,rotate
from .assets import canonical


def box_cells(size):
    vector(size)
    if any(v<=0 for v in size):raise ValueError('Positive box dimensions required')
    v=[[size[0]*((i&1)-.5),size[1]*(((i>>1)&1)-.5),size[2]*(((i>>2)&1)-.5)] for i in range(8)]
    return [[v[i] for i in indices] for indices in ((0,1,3,7),(0,3,2,7),(0,2,6,7),(0,6,4,7),(0,4,5,7),(0,5,1,7))]


def inertia(size,mass):
    x,y,z=size
    return [mass*(y*y+z*z)/12,mass*(x*x+z*z)/12,mass*(x*x+y*y)/12]


def tensor(q,diagonal,inverse=False):
    columns=[rotate(q,axis) for axis in ([1,0,0],[0,1,0],[0,0,1])]
    diagonal=[1/v for v in diagonal] if inverse else diagonal
    return [[sum(columns[k][i]*diagonal[k]*columns[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def matvec(matrix,v):return [snow.dot(row,v) for row in matrix]


def step(body,controls,world,dt,config):
    canonical([body,controls,dt,config])
    if not 0<dt<=1/60:raise ValueError('Rigid cell mode requires dt <= 1/60')
    cfg=config.get('rigid',{})
    if config.get('sport','snowboard') not in ('snowboard','ski'):raise ValueError('Rigid cells support snow sports only')
    size=cfg.get('size',[1.6,.28,.12]);cells=box_cells(size);mass=body['mass']
    if mass<=0:raise ValueError('Positive mass required')
    gravity=cfg.get('gravity',9.81)
    if not math.isfinite(gravity) or gravity<0:raise ValueError('Nonnegative gravity required')
    b=copy.deepcopy(body);p=vector(b['position']);q=normalize(vector(b['orientation'],4));v=vector(b['velocity'])
    diag=inertia(size,mass);iw=tensor(q,diag,True)
    state=b.setdefault('_rigid',{})
    momentum=vector(state.get('angular_momentum',matvec(tensor(q,diag),b['angular_velocity'])))
    omega=matvec(iw,momentum);old_grounded=b['grounded'];events=[]
    sample=world.sample(p[0],p[1]);n=sample['normal'];material=sample['material']
    surface=dict(normal=n,point=[p[0],p[1],sample['height']],velocity=sample['velocity'],material=material)
    total_volume=sum(snow.tetra_volume(cell) for cell in cells)
    pressure=[0.,0.,0.];contact=[0.,0.,0.];torque=[0.,0.,0.];wet=0.;cell_results=[]
    # Simultaneous force evaluation from one pre-force state; order is our policy.
    for local in cells:
        vertices=[snow.add(p,rotate(q,point)) for point in local]
        settings=dict(face_weight=snow.tetra_volume(local),total_weight=total_volume,face_normal=n,depth_curve={'domain':[0,1],'$array':[1,1]},gravity=-gravity)
        result=evaluate_cell(b,vertices,surface,dt,settings)
        wet+=result['submerged_volume']
        if result['submerged_volume']:
            pressure=list(snow.add(pressure,result['pressure_impulse']));contact=list(snow.add(contact,result['contact_impulse']))
            j=snow.add(result['pressure_impulse'],result['contact_impulse']);torque=list(snow.add(torque,snow.cross(snow.sub(result['centroid'],p),j)))
        cell_results.append(dict(volume=result['submerged_volume']))
    fraction=min(1.,wet/total_volume);grounded=wet>1e-9
    j=snow.add(pressure,contact);v=list(snow.add(v,snow.mul(j,1/mass)));v[2]-=gravity*dt
    momentum=list(snow.add(momentum,torque))
    forward=rotate(q,[1,0,0]);lateral=rotate(q,[0,1,0])
    if grounded:
        # Designed bounded lateral grip. All recovered cell impulses remain separate.
        slip=snow.dot(v,lateral);grip=material['grip']*gravity*fraction
        dv=max(-grip*dt,min(grip*dt,-slip))
        v=list(snow.add(v,snow.mul(lateral,dv)))
        yaw_rate=snow.dot(matvec(iw,momentum),n);desired=float(controls.get('steer',0))*1.2
        momentum=list(snow.add(momentum,snow.mul(n,(desired-yaw_rate)*diag[2]*min(1.,5*dt)*fraction)))
        if controls.get('brake'):
            tangent=snow.sub(v,snow.mul(n,snow.dot(v,n)));speed=snow.norm(tangent)
            if speed:v=list(snow.sub(v,snow.mul(tangent,min(speed,6*dt)/speed)))
        if controls.get('tuck'):v=list(snow.add(v,snow.mul(forward,dt)))
        if controls.get('jump'):state['charge']=min(.7,state.get('charge',0)+dt)
        elif state.get('jump_held'):
            speed=2+state.get('charge',0)/.7*2.5;v=list(snow.add(v,snow.mul(n,speed)));events.append(dict(type='jump',speed=speed,policy='synthetic'));state['charge']=0
    else:
        state['charge']=0.
        torque_input=snow.add([0,0,float(controls.get('steer',0))*3],snow.mul(lateral,float(controls.get('flip',0))*3))
        momentum=list(snow.add(momentum,snow.mul(torque_input,dt)))
    state['jump_held']=bool(controls.get('jump'))
    omega=matvec(iw,momentum);rate=snow.norm(omega)
    if rate:
        dq=[*(x*math.sin(rate*dt/2)/rate for x in omega),math.cos(rate*dt/2)]
        q=normalize(skeleton.qmul(dq,q))
    p=list(snow.add(p,snow.mul(v,dt)))
    # Synthetic solid substrate beneath the material layer, at lowest hull point.
    terrain=world.sample(p[0],p[1]);bottom=min(rotate(q,x)[2] for cell in cells for x in cell)
    substrate=terrain['height']-terrain['material']['thickness']
    if p[2]+bottom<substrate:
        p[2]=substrate-bottom;vn=snow.dot(v,terrain['normal'])
        if vn<0:v=list(snow.sub(v,snow.mul(terrain['normal'],vn)))
        grounded=True
    if grounded and not old_grounded:
        impact=max(0.,-snow.dot(body['velocity'],n));alignment=snow.dot(rotate(q,[0,0,1]),n)
        quality='crash' if impact>10 or alignment<.25 else 'sketchy' if impact>5 or alignment<.8 else 'clean'
        events.append(dict(type='landing',quality=quality,impact_speed=impact,policy='synthetic'))
    state['angular_momentum']=momentum
    b.update(position=p,velocity=v,orientation=q,angular_velocity=matvec(tensor(q,diag,True),momentum),grounded=grounded)
    canonical(b);body.clear();body.update(b)
    return dict(sport=config.get('sport','snowboard'),mode='rigid_cells',events=events,grounded=grounded,speed=snow.norm(v),submerged_volume=wet,total_volume=total_volume,immersion=fraction,pressure_impulse=pressure,contact_impulse=contact,torque_impulse=torque,cells=cell_results,evidence='recovered cell and point-impulse math; synthetic hull/contact weighting/control/substrate and integration')
