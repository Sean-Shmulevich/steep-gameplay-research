"""Two-body point motion; LINK_SOLVER.md, Paired-builder relative point motion."""
import math
from reference.central_impulse import f32


def paired_link_point_motion(first, second, first_point, second_point):
    """Recover both offset-relative arms and second-minus-first point motion.

    Body dictionaries supply frame, offset128, motion1a0 and motion1ac. Structural
    field names retain uncertain units. Finite XYZ output only; no SIMD padding.
    """
    def vector(values):
        if len(values)!=3:raise ValueError('Three components required')
        result=[f32(v) for v in values]
        if not all(math.isfinite(v) for v in result):raise ValueError('Finite components required')
        return result
    outputs=[]
    for body,point in ((first,first_point),(second,second_point)):
        frame=body['frame']
        if len(frame['basis'])!=3:raise ValueError('Three basis rows required')
        basis=[vector(v) for v in frame['basis']]
        translation=vector(frame['translation']);center=vector(body['offset128'])
        point=vector(point);linear=vector(body['motion1a0']);angular=vector(body['motion1ac'])
        def transform(v):
            return [f32(f32(basis[2][i]*v[2])+f32(f32(basis[0][i]*v[0])+f32(basis[1][i]*v[1]))) for i in range(3)]
        rotated_center=transform(center)
        world_center=[f32(translation[i]+rotated_center[i]) for i in range(3)]
        arm=transform([f32(point[i]-center[i]) for i in range(3)])
        spin=[f32(f32(angular[(i+1)%3]*arm[(i+2)%3])-f32(arm[(i+1)%3]*angular[(i+2)%3])) for i in range(3)]
        motion=[f32(spin[i]+linear[i]) for i in range(3)]
        outputs.append(dict(center_world=world_center,arm=arm,point_motion=motion))
    return dict(first=outputs[0],second=outputs[1],
                relative_motion=[f32(outputs[1]['point_motion'][i]-outputs[0]['point_motion'][i]) for i in range(3)])


def paired_link_tangent_basis(relative_motion, normal):
    """Project paired relative motion and select the inspected fallback tangent.

    Normal is supplied, not normalized. The first tangent's fourth lane is exposed
    because paired positive-zero motion differs from the single-family negation.
    """
    def vector(values):
        if len(values)!=3:raise ValueError('Three components required')
        result=[f32(v) for v in values]
        if not all(math.isfinite(v) for v in result):raise ValueError('Finite components required')
        return result
    motion=vector(relative_motion);n=vector(normal)
    def dot(a,b):
        p=[f32(x*y) for x,y in zip(a,b)]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.0))
    projection=dot(motion,n)
    tangent=[f32(motion[i]-f32(projection*n[i])) for i in range(3)]
    fallback=f32(dot(tangent,tangent)-f32(1e-6))<0
    if fallback:
        x,y,z=n;ax,ay,az=map(abs,n)
        if f32(min(ax,ay)-az)<0:
            tangent=[z,0.0,-x] if f32(ay-ax)<0 else [0.0,z,-y]
        else:tangent=[y,-x,0.0]
    length=f32(math.sqrt(dot(tangent,tangent)))
    if not length or not math.isfinite(length):raise ValueError('Finite nonzero tangent required')
    inverse=f32(1.0/length)
    first=[f32(v*inverse) for v in tangent]
    second=[f32(f32(n[(i+1)%3]*first[(i+2)%3])-f32(first[(i+1)%3]*n[(i+2)%3])) for i in range(3)]
    lane3=0.0 if fallback else f32(0.0-f32(projection*0.0))
    return dict(first=first,second=second,first_lane3=f32(lane3*inverse),
                relative_motion_projection=projection,fallback=fallback)
