"""Recovered local velocity-correction decisions with supplied upstream inputs.

Evidence: CENTRAL_IMPULSE.md, Post-submission velocity setter and speed floor.
Damping curves, frame transforms, activation and native setter remain external.
"""
from math import sqrt
from reference.central_impulse import f32
from .snow_post_pending import four


def speed(vector):
    squares=[f32(x*x) for x in vector[:3]]
    return f32(sqrt(f32(squares[0]+f32(squares[1]+squares[2]))))


def preserve_speed_floor(original, candidate, floor, bypass):
    """Finite XYZ velocities; W zeroed as in the surrounding native producers.

    Local branch RVA 0x13f81e0..0x13f8225. No global minimum-speed policy:
    original speeds below the floor are preserved rather than accelerated.
    """
    if type(bypass) is not bool:
        raise ValueError('Explicit bypass boolean required')
    original=four(original);candidate=four(candidate)
    original[3]=candidate[3]=0.0
    floor=f32(floor);old_speed=speed(original);new_speed=speed(candidate)
    if bypass or floor <= new_speed:
        return dict(velocity=candidate,speed=new_speed,action='candidate')
    if old_speed > floor:
        return dict(velocity=[f32(f32(floor*x)/old_speed) for x in original],
                    speed=floor,action='original_direction_at_floor')
    return dict(velocity=original,speed=old_speed,action='original')
