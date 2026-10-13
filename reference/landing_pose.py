"""Portable finite-input pose math; synthetic examples, not a complete controller."""
import math
import json

CROSS_EPS = 0.009999999776482582
MOTION_EPS = 0.000009999999747378752
DELAY_SCALE = 0.8999999761581421
IDENTITY = ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))

def dot(a, b):
    return sum(x*y for x, y in zip(a, b))

def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

def norm(v):
    return math.sqrt(dot(v, v))

def unit(v):
    n = norm(v)
    if n == 0:
        raise ValueError('Zero direction')
    return tuple(x/n for x in v)

def alignment_weight(elapsed, horizon, minimum_horizon, start_marker=0.):
    # Explicit domain policy: exceptions replace undefined divisions.
    if horizon > minimum_horizon:
        if horizon == 0:
            raise ValueError('Zero horizon')
        weight = elapsed/horizon
    else:
        weight = 0.
    if start_marker > 0:
        if horizon == start_marker:
            raise ValueError('Coincident horizon and start marker')
        weight = DELAY_SCALE*(elapsed-start_marker)/(horizon-start_marker)
    return min(1., max(0., weight))

def rotate(vector, axis, angle):
    axis = unit(axis)
    c, s = math.cos(angle), math.sin(angle)
    k = cross(axis, vector)
    d = dot(axis, vector)
    return tuple(vector[i]*c+k[i]*s+axis[i]*d*(1-c) for i in range(3))

def align_basis(basis, source, target, weight):
    axis = cross(source, target)
    if norm(axis) <= CROSS_EPS:
        return tuple(tuple(v) for v in basis)
    cosine = max(-1., min(1., dot(unit(source), unit(target))))
    angle = math.acos(cosine)*weight
    return tuple(rotate(v, axis, angle) for v in basis)

def delayed_response(elapsed, delay, gain, tau):
    if tau <= 0:
        raise ValueError('Portable helper requires positive tau')
    t = elapsed-delay
    return 0. if t < 0 else -gain*(tau*math.expm1(-t/tau)+t)

def tilt_basis(basis, cached_motion, angle):
    horizontal = (cached_motion[0], cached_motion[1], 0.)
    if all(abs(x) <= MOTION_EPS for x in horizontal):
        return tuple(tuple(v) for v in basis)
    axis = cross((0., 0., 1.), unit(horizontal))
    return tuple(rotate(v, axis, angle) for v in basis)

def shifted_translation(translation, position_a, position_b):
    return tuple(translation[i]-(position_a[i]-position_b[i]) for i in range(3))+(1.,)

def examples():
    return {
        'ordinary_halfway_weight': alignment_weight(.5, 1., .1),
        'delayed_weight_at_horizon': alignment_weight(1., 1., .1, .2),
        'half_alignment_up': align_basis(IDENTITY, (0.,0.,1.), (1.,0.,0.), .5)[2],
        'antiparallel_unchanged': align_basis(IDENTITY, (0.,0.,1.), (0.,0.,-1.), 1.),
        'negative_tilt_up': tilt_basis(IDENTITY, (10.,0.,3.), -.2)[2],
        'response_at_one': delayed_response(1., .2, .3, .1),
        'translation': shifted_translation((1.,2.,3.), (4.,5.,6.), (2.,3.,4.))
    }

if __name__ == '__main__':
    print(json.dumps(examples(), indent=2))
