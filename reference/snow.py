"""Portable documented snow equations. Tuned material curves are explicit inputs.
Python arithmetic is not a bit-exact replacement for the float32/SIMD arithmetic.
"""
import math, json

def add(a, b):
    return tuple((x + y for x, y in zip(a, b)))

def sub(a, b):
    return tuple((x - y for x, y in zip(a, b)))

def mul(a, s):
    return tuple((x * s for x in a))

def dot(a, b):
    return sum((x * y for x, y in zip(a, b)))

def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

def norm(a):
    return math.sqrt(dot(a, a))

def unit(a):
    return mul(a, 1 / norm(a))

def clamp(x, a, b):
    return min(max(x, a), b)
FOUR_PI_SQUARED = 39.47842025756836

def frequency_strength(effective_mass, frequency):
    return clamp(effective_mass * frequency * frequency * FOUR_PI_SQUARED, 1.0000000116860974e-07, 999999995904.0)

def contact_forces(normal, relative_velocity, dt, effective_mass, normal_frequency, tangent_frequency, surface_frequency=0.0, hull_mode=True, depth_fraction=1.0):
    fn = (0.0, 0.0, 0.0)
    ft = fn
    vn = dot(normal, relative_velocity)
    vt = sub(relative_velocity, mul(normal, vn))
    if norm(relative_velocity) > 9.999999747378752e-05 and effective_mass > 0 and (depth_fraction > 0):
        if abs(vn) > 9.999999747378752e-05:
            strength = frequency_strength(effective_mass, normal_frequency)
            fn = mul(normal, -strength * dt * vn)
            stop_limit = effective_mass * abs(vn) / dt
            if norm(fn) > stop_limit:
                fn = mul(fn, stop_limit / norm(fn))
        if norm(vt) > 9.999999747378752e-05:
            strength = frequency_strength(effective_mass, tangent_frequency)
            ft = mul(vt, -strength * dt)
    if hull_mode and surface_frequency > 0:
        fn = add(fn, mul(normal, frequency_strength(effective_mass, surface_frequency)))
    force = add(fn, ft)
    return dict(normal_force=fn, tangent_force=ft, force=force, impulse=mul(force, dt))

def plane_depth_fraction(normal, offset, point, thickness):
    if thickness <= 0:
        return 1.0
    signed = dot(normal, point) + offset
    if abs(normal[2]) > 0.0005099999834783375:
        vertical_depth = -signed / normal[2]
    elif abs(signed) > 0.0005099999834783375:
        return 0.0
    else:
        vertical_depth = 0.0
    return clamp(vertical_depth / thickness, 0.0, 1.0)

def edge_intersection(normal, offset, a, b):
    d = sub(b, a)
    den = dot(normal, d)
    if abs(den) <= 0.0005099999834783375:
        if abs(dot(normal, a) + offset) > 0.0005099999834783375 and abs(dot(normal, b) + offset) > 0.0005099999834783375:
            return None
        return a
    return add(a, mul(d, -(dot(normal, a) + offset) / den))

def tetra_volume(vertices):
    a, b, c, d = vertices
    return abs(dot(sub(b, a), cross(sub(c, a), sub(d, a)))) / 6.0

def tetra_centroid(vertices):
    return tuple((sum((v[j] for v in vertices)) / 4 for j in range(3)))

def pressure_force(plane_normal, rho, submerged_volume, depth_gain):
    return mul(plane_normal, rho * submerged_volume * depth_gain)

def pressure_impulse(plane_normal, rho, volume, depth_gain, gravity_z_abs, tilt_gain, speed_gain, activation, dt):
    return mul(pressure_force(plane_normal, rho, volume, depth_gain), gravity_z_abs * tilt_gain * speed_gain * activation * dt)

def ground_stick_speed_envelope(speed, mode_a=False, mode_b=False):
    if speed >= 30 and (not (mode_a or mode_b)):
        return 0.0
    if speed < 15:
        return speed * 2
    if mode_a or mode_b:
        return 30.0
    return (30 - speed) * 2

def ground_stick_impulses(direction, directional_alignment, leg_gain, depth_gain, speed, mode_a, mode_b, boost_multiplier, ground_time, mode_scale, dt, rider_mass, total_mass, speed_curve_gain=1.0, external_scale=1.0):
    if speed_curve_gain <= 0.10000000149011612:
        return None
    timer = 1.0 if mode_a else min(ground_time * 6.0, 1.0)
    scale = mode_scale if mode_a else 1.0
    acceleration = -leg_gain * directional_alignment * depth_gain * ground_stick_speed_envelope(speed, mode_a, mode_b) * boost_multiplier * timer * scale
    if acceleration >= -0.1:
        return None
    dv = mul(direction, acceleration * dt * external_scale)
    return dict(acceleration=mul(direction, acceleration), delta_velocity=dv, rider_impulse=mul(dv, rider_mass), board_impulse=mul(dv, total_mass - rider_mass))

def clipped_tetra(vertices, normal, offset):
    wet = [v for v in vertices if dot(normal, v) + offset <= 0]
    dry = [v for v in vertices if dot(normal, v) + offset > 0]
    full = tetra_volume(vertices)
    center = tetra_centroid(vertices)
    if not wet:
        return (0.0, None)
    if len(wet) == 4:
        return (full, center)
    if len(wet) == 1:
        w = wet[0]
        tet = [w] + [edge_intersection(normal, offset, w, d) for d in dry]
        return (tetra_volume(tet), tetra_centroid(tet))
    if len(wet) == 3:
        d = dry[0]
        tet = [d] + [edge_intersection(normal, offset, d, w) for w in wet]
        removed = tetra_volume(tet)
        v = full - removed
        return (v, mul(sub(mul(center, full), mul(tetra_centroid(tet), removed)), 1 / v))
    a, b = wet
    c, d = dry
    e = edge_intersection(normal, offset, c, a)
    f = edge_intersection(normal, offset, a, d)
    g = edge_intersection(normal, offset, d, b)
    h = edge_intersection(normal, offset, b, c)
    tets = [(a, b, e, g), (f, a, e, g), (h, b, e, g)]
    volumes = [tetra_volume(t) for t in tets]
    v = sum(volumes)
    centroid = tuple((sum((w * tetra_centroid(t)[j] for w, t in zip(volumes, tets))) / v for j in range(3)))
    return (v, centroid)
import struct

def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]

def normalized_asin_lut(padding=f32(0.0005)):
    xmin = -1.0
    xmax = 1.0
    width = f32(xmax - xmin)
    step = f32(width * f32(1 / 256))
    domain_min = f32(xmin - f32(width * padding))
    scale = f32(256 / f32(f32(f32(padding + 1) * width) + f32(xmin - domain_min)))
    samples = [f32(f32(math.asin(f32(f32(i * step) + xmin))) * f32(0.6366197466850281)) for i in range(257)]
    segments = []
    for i in range(256):
        m = f32(f32(samples[i + 1] - samples[i]) / step)
        intercept = f32(samples[i] - f32(f32(f32(i * step) + xmin) * m))
        segments.append((m, intercept))
    return dict(domain_min=domain_min, index_scale=scale, segments=segments)

def eval_normalized_asin_lut(x, lut=None):
    lut = lut or normalized_asin_lut()
    x = f32(x)
    location = f32(f32(x - lut['domain_min']) * lut['index_scale'])
    if location < 0:
        i = 0
        x = lut['domain_min']
    else:
        i = math.floor(location)
        if i > 255:
            i = 255
            x = f32(f32(256 / lut['index_scale']) + lut['domain_min'])
    m, b = lut['segments'][i]
    return f32(f32(x * m) + b)

def coefficient_inputs(face_normal, relative_velocity, plane_normal, lut=None):
    lut = lut or normalized_asin_lut()
    vn = dot(face_normal, relative_velocity)
    speed = norm(relative_velocity)
    vt = sub(relative_velocity, mul(face_normal, vn))
    ts = norm(vt)
    sign = 0 if vn == 0 else 1 if vn > 0 else -1
    return dict(flow=eval_normalized_asin_lut(-clamp(vn / speed, -1, 1), lut), normal_speed=abs(vn), tangent_speed=ts, surface_normal=-eval_normalized_asin_lut(clamp(dot(face_normal, plane_normal) * sign, -1, 1), lut), surface_tangent=eval_normalized_asin_lut(clamp(dot(mul(vt, -1 / ts), plane_normal), -1, 1), lut) if ts else 0, push_branch=vn > 0)
from pathlib import Path
import json
import math

def preset_weight(runtime_speed, normal_threshold=7.0, fast_threshold=12.0):
    return clamp((runtime_speed * 3.6 - normal_threshold) / (fast_threshold - normal_threshold), 0.0, 1.0)

def blend(normal, fast, weight):
    return normal * (1.0 - weight) + fast * weight

def molded_curve(curve, value):
    samples = curve['$array']
    low, high = curve['domain']
    count = len(samples) - 1
    step = (high - low) / count
    epsilon = min((high - low) * 0.0001, 0.0001)
    scale = count / (high - low + 2.0 * epsilon)
    value = clamp(value, low - epsilon, high + epsilon)
    segment = min(int(math.floor((value - (low - epsilon)) * scale)), count - 1)
    slope = (samples[segment + 1] - samples[segment]) / step
    intercept = samples[segment] - (low + segment * step) * slope
    return slope * value + intercept

def decay_lookup(value):
    low, high, count = (-10.0, 0.0, 256)
    step = (high - low) / count
    padding = (high - low) * 0.0001
    start = low - padding
    scale = count / (high - low + 2.0 * padding)
    value = clamp(value, start, count / scale + start)
    segment = min(int(math.floor((value - start) * scale)), count - 1)
    x0 = low + segment * step
    y0, y1 = (math.exp(x0), math.exp(x0 + step))
    slope = (y1 - y0) / step
    return slope * value + y0 - x0 * slope

def cooker(current, target, dt, coefficients, epsilon=0.0001):
    direction = 'ToZero' if abs(target) <= abs(current) or current * target <= 0 else 'ToOne'
    base = coefficients['baseDampFactor' + direction]
    proportional = coefficients['proportionalDampFactor' + direction]
    step = (1.0 - decay_lookup(-dt * proportional)) * abs(target - current) + dt * base
    result = current + math.copysign(min(step, abs(target - current)), target - current)
    return target if abs(target - result) < epsilon else result

def shape_axis(raw, boost_weight, strength_boost, sum_cutoff, sum_excess_weight):
    magnitude = min(abs(raw), sum_cutoff) + max(abs(raw) - sum_cutoff, 0.0) * sum_excess_weight
    return clamp(math.copysign(magnitude, raw) * (1.0 + boost_weight * (strength_boost - 1.0)), -1.0, 1.0)

def attenuate_steering(x, y, normal, fast, weight):
    horizontal_gain = blend(molded_curve(normal['horizontal']['attenuationCurve'], y), molded_curve(fast['horizontal']['attenuationCurve'], y), weight)
    vertical_gain = blend(molded_curve(normal['vertical']['attenuationCurve'], x), molded_curve(fast['vertical']['attenuationCurve'], x), weight)
    return (x * horizontal_gain, y * vertical_gain)

def rider_spring(position, velocity, target_position, target_velocity, mass, stiffness, damping, external_acceleration, dt, substeps=10):
    h = dt / substeps
    for _ in range(substeps):

        def acceleration(p, v):
            return ((target_position - p) * stiffness + (target_velocity - v) * damping) / mass + external_acceleration
        k1p, k1v = (velocity, acceleration(position, velocity))
        k2p = velocity + k1v * h / 2.0
        k2v = acceleration(position + k1p * h / 2.0, k2p)
        k3p = velocity + k2v * h / 2.0
        k3v = acceleration(position + k2p * h / 2.0, k3p)
        k4p = velocity + k3v * h
        k4v = acceleration(position + k3p * h, k4p)
        position += h * (k1p + 2 * k2p + 2 * k3p + k4p) / 6.0
        velocity += h * (k1v + 2 * k2v + 2 * k3v + k4v) / 6.0
        target_position += target_velocity * h
    return (position, velocity, target_position)

def material_controls(leg_coil,buttering_angle,steering_horizontal):
    return {'legCoilCurve':leg_coil,'butteringCurve':clamp(abs(buttering_angle)/(math.pi/2),0,1),'steeringCurve':abs(steering_horizontal)}

def material_frequency(record,coordinates):
    product=1.0
    for key in ('flowAngleCurve','legCoilCurve','butteringCurve','steeringCurve',
                'normalSpeedCurve','tangentialSpeedCurve','surfaceAngleCurve','depthCurve'):
        product*=max(0.0,molded_curve(record[key],coordinates[key]))
    return max(0.0,product)*record['baseMultiplier']

def selected_material_blocks(hull_mode,flow_angle):
    return ('hull' if hull_mode else 'foil')+('Push' if flow_angle<0 else 'Pull'),('hullDrag' if hull_mode else 'foilDrag')

def weighted_direction_history(samples,now,duration,curve):
    if duration<=0:raise ValueError('positive averaging duration required')
    retained=[(molded_curve(curve,(now-t)/duration),v) for t,v in samples if now-t<=duration]
    total=sum(w for w,v in retained)
    if not total:raise ValueError('nonzero history weight required')
    return tuple(sum(w*v[j] for w,v in retained)/total for j in range(3))

def attitude_angle(runtime_angle,speed,immersion,speed_curve,immersion_curve):
    return runtime_angle*molded_curve(speed_curve,speed)*molded_curve(immersion_curve,immersion)

def point_relative_velocity(body_velocity,angular_velocity,point,center_of_mass,material_velocity):
    return sub(add(body_velocity,cross(angular_velocity,sub(point,center_of_mass))),material_velocity)

def apply_point_impulse(velocity,angular_velocity,impulse,point,center_of_mass,mass,inverse_world_inertia):
    torque=cross(sub(point,center_of_mass),impulse)
    angular_delta=tuple(dot(row,torque) for row in inverse_world_inertia)
    return add(velocity,mul(impulse,1/mass)),add(angular_velocity,angular_delta)

def cell_step(vertices,plane_normal,plane_offset,layer_thickness,fluid_density,
              depth_curve,pressure_tilt_gain,pressure_speed_gain,gravity_z,
              pressure_activation,dt,face_normal,face_contact_weight,total_mass,
              total_contact_weight,contact_activation,relative_velocity,
              normal_frequency,tangent_frequency,surface_frequency=0,hull_mode=True):
    volume,centroid=clipped_tetra(vertices,plane_normal,plane_offset)
    if volume==0:return {'submerged_volume':0.0,'pressure_impulse':(0,0,0),'contact_impulse':(0,0,0)}
    depth=plane_depth_fraction(plane_normal,plane_offset,centroid,layer_thickness)
    jp=pressure_impulse(plane_normal,fluid_density,volume,molded_curve(depth_curve,depth),
                        abs(gravity_z),pressure_tilt_gain,pressure_speed_gain,pressure_activation,dt)
    effective_mass=contact_activation*total_mass/total_contact_weight*face_contact_weight
    contact=contact_forces(face_normal,relative_velocity,dt,effective_mass,normal_frequency,
                           tangent_frequency,surface_frequency,hull_mode,depth)
    return {'submerged_volume':volume,'centroid':centroid,'depth_fraction':depth,
            'pressure_impulse':jp,'contact_impulse':contact['impulse'],'contact_force':contact['force']}

def worked_examples():
    constant={'domain':[0,1],'$array':[1,1]}
    cell=cell_step([(0,0,-1),(1,0,-1),(0,1,-1),(0,0,0)],(0,0,1),0,1,
                  1000,constant,1,1,-9.81,1,1/60,(0,0,-1),.5,80,2,1,(2,0,-3),2,1,.5)
    return {'synthetic_cell':cell,'controls':material_controls(.4,math.pi/4,-.6),
            'preset_weights':[preset_weight(v) for v in (0,7/3.6,9.5/3.6,12/3.6)],
            'speed_envelope':[(v,ground_stick_speed_envelope(v)) for v in (0,5,15,25,30)],
            'ground_stick':ground_stick_impulses((0,0,1),1,1,.5,5,False,False,1,.2,1,1/60,20,80),
            'scalar_spring':rider_spring(0,0,.1,0,20,frequency_strength(20,4),
                         2*.5*math.sqrt(20*frequency_strength(20,4)),0,1/60),
            'history':weighted_direction_history([(0,(1,0,0)),(.375,(0,1,0)),(.75,(0,0,1))],.75,.75,
                         {'domain':[0,1],'$array':[1,.375]}),
            'angle_lookup':[(v,eval_normalized_asin_lut(v)) for v in (-1,-.5,0,.5,1)]}

if __name__=='__main__':print(json.dumps(worked_examples(),indent=2))
