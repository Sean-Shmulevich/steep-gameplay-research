"""Finite normal/fast input profile arithmetic with float32 ordering.

See CENTRAL_IMPULSE.md, 'Input speed profile selection'. Thresholds are in
converted speed units; the supplied runtime speed is multiplied by 3.6 first.
"""
from reference.central_impulse import f32


def preset_weight(runtime_speed, normal_threshold=7., fast_threshold=12.):
    speed=f32(f32(runtime_speed)*f32(3.6))
    normal,fast=map(f32,(normal_threshold,fast_threshold))
    # Preserve branch priority even for equal or reversed finite thresholds.
    if speed <= normal:
        return 0.
    if speed >= fast:
        return 1.
    return f32(f32(speed-normal)/f32(fast-normal))


def blend(normal, fast, weight):
    normal,fast,weight=map(f32,(normal,fast,weight))
    return f32(f32(f32(f32(1)-weight)*normal)+f32(weight*fast))
