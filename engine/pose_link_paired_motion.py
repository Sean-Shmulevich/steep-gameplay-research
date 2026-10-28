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
