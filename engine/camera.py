"""Synthetic follow policy using recovered camera spring and projection math."""
import math
from reference import camera
from .math3d import rotate
from .assets import canonical

def update(state,body,dt,config=None):
    config=config or {};canonical([state,body,dt,config])
    if dt<0:raise ValueError('Negative camera dt')
    distance=config.get('distance',6.);height=config.get('height',3.);omega=config.get('frequency',6.)
    if distance<0 or height<0 or omega<0:raise ValueError('Invalid camera tuning')
    forward=rotate(body['orientation'],[1,0,0]);target=[body['position'][i]-distance*forward[i]+(height if i==2 else 0) for i in range(3)]
    p,v=camera.vector_spring(state.get('position',target),state.get('velocity',[0,0,0]),target,omega,dt)
    state.update(position=p,velocity=v,target=list(body['position']),vertical_fov=config.get('vertical_fov',math.radians(65)),evidence='recovered spring; synthetic follow policy and explicit vertical FOV')
    return state
