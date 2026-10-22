"""Cached-velocity projection magnitude with recovered float32 ordering.

CENTRAL_IMPULSE.md, 'Projected input speed'. The caller supplies the projection
normal; this leaf neither normalizes it nor subtracts surface velocity.
"""
import math
from reference.central_impulse import f32


def projected_speed(velocity, normal):
    if len(velocity)!=3 or len(normal)!=3:
        raise ValueError('Three-component velocity and normal required')
    velocity=tuple(map(f32,velocity));normal=tuple(map(f32,normal))
    products=[f32(a*b) for a,b in zip(velocity,normal)]
    dot=f32(products[0]+f32(products[1]+products[2]))
    tangent=tuple(f32(v-f32(dot*n)) for v,n in zip(velocity,normal))
    squares=[f32(v*v) for v in tangent]
    squared=f32(squares[0]+f32(squares[1]+squares[2]))
    return {'speed':f32(math.sqrt(squared)),'projected_velocity':tangent,'normal_dot':dot}
