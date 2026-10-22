"""Evaluator channel gathering when the retained context has no visible target.

Evidence: CENTRAL_IMPULSE.md, Context-free animation work transforms.
Range and shape checks are inspection policy; native code trusts its metadata.
"""
from reference.ground_response_pose import provider_pose_transform


def gather_work_transforms(records, indices, parent_position, parent_rotation, direct):
    records, indices = list(records), list(indices)
    if len(indices) > 65535:
        raise ValueError('uint16 channel count required')
    if any(type(i) is not int or not 0 <= i <= 65535 or i >= len(records) for i in indices):
        raise ValueError('channel index outside supplied records')
    output = []
    for i in indices:
        record = records[i]
        if len(record) != 2:
            raise ValueError('position/rotation record pair required')
        output.append(provider_pose_transform(record[0], record[1],
                      parent_position, parent_rotation, direct))
    return output


def gather_context_work(records, indices, parent_position, parent_rotation, direct,
                        context_position, context_rotation, reciprocal_sqrt):
    """Apply an already-converted context transform and normalize rotations.

    Context position W is the supplied scale. Obtaining/inverting the target
    transform is outside this kernel. reciprocal_sqrt supplies the hardware seed;
    a perfect reciprocal square root is a numerical substitute, not bit parity.
    """
    import math
    from reference.snow import f32
    context_position = tuple(map(f32, context_position))
    context_rotation = tuple(map(f32, context_rotation))
    if len(context_position) != 4 or len(context_rotation) != 4 or not all(
            math.isfinite(x) for x in context_position + context_rotation):
        raise ValueError('finite four-lane context required')
    gathered = gather_work_transforms(records, indices, parent_position, parent_rotation, direct)
    output = []
    for row in gathered:
        p = row['position']
        scaled = tuple(f32(x * context_position[3]) for x in p[:3]) + (0.,)
        result = provider_pose_transform(scaled, row['rotation'], context_position,
                                         context_rotation, False)
        result['position'] = result['position'][:3] + (f32(context_position[3] * p[3]),)
        q = result['rotation']
        squares = tuple(f32(x*x) for x in q)
        n = f32(f32(squares[0]+squares[2])+f32(squares[1]+squares[3]))
        if not math.isfinite(n) or n <= 0:
            raise ValueError('positive finite rotation norm required by inspection adapter')
        seed = f32(reciprocal_sqrt(n))
        factor = f32(f32(f32(.5 * seed)) * f32(3. - f32(f32(seed*n)*seed)))
        result['rotation'] = tuple(f32(factor*x) for x in q)
        output.append(result)
    return output


def invert_context_transform(position_scale, rotation):
    """Recovered transform inverse; zero scale uses one, quaternion is not normalized.

    Caller supplies the normalized rotation used by the animation caller. Finite
    inputs are an inspection restriction, not a native guard.
    """
    import math
    from reference.snow import f32
    p, q = tuple(map(f32, position_scale)), tuple(map(f32, rotation))
    if len(p) != 4 or len(q) != 4 or not all(math.isfinite(x) for x in p+q):
        raise ValueError('finite four-lane context required')
    inverse_q = tuple(-x for x in q[:3]) + (q[3],)
    scale = 1. if p[3] == 0 else p[3]
    x, y, z, w = inverse_q
    dot = f32(f32(x*p[0]) + f32(f32(y*p[1])+f32(z*p[2])))
    cross = (f32(f32(y*p[2])-f32(z*p[1])),
             f32(f32(z*p[0])-f32(x*p[2])),
             f32(f32(x*p[1])-f32(y*p[0])))
    wterm = f32(f32(w*w)-.5)
    rotated = tuple(f32(f32(f32(f32(c*w)+f32(dot*a))+f32(wterm*b))*2.)
                    for c,a,b in zip(cross,inverse_q,p))
    return dict(position=tuple(f32(-x/scale) for x in rotated)+(f32(1./scale),),
                rotation=inverse_q)


def convert_raw_context(basis_rows, position, reciprocal_sqrt):
    """Animation caller's matrix-to-normalized-inverse transform pipeline.

    The caller masks position W to zero before inversion, so the inverse helper
    uses its unit-scale fallback. Raw position W does not supply context scale.
    """
    from reference.ground_response_pose import entity_pose_transform
    from reference.snow import f32
    q = entity_pose_transform(basis_rows, position, 0.)['rotation']
    squares = tuple(f32(x*x) for x in q)
    n = f32(f32(squares[0]+squares[2])+f32(squares[1]+squares[3]))
    seed = f32(reciprocal_sqrt(n))
    factor = f32(f32(.5*seed)*f32(3.-f32(f32(seed*n)*seed)))
    normalized = tuple(f32(x*factor) for x in q)
    return invert_context_transform(tuple(position[:3])+(0.,), normalized)


def gather_raw_context_work(records, indices, parent_position, parent_rotation,
                            direct, basis_rows, position, reciprocal_sqrt):
    """Compose recovered kernels; seed callback is consumed in execution order."""
    context = convert_raw_context(basis_rows, position, reciprocal_sqrt)
    return gather_context_work(records, indices, parent_position, parent_rotation,
                               direct, context['position'], context['rotation'],
                               reciprocal_sqrt)


def encode_work_pose(position, rotation, parent_position, parent_rotation, direct):
    """Convert an application-space record to bank storage; no flags or allocation.

    The composed setter ignores parent scale and stores position W as zero.
    Direct mode copies all lanes. No quaternion normalization is inserted.
    """
    if type(direct) is not bool:
        raise ValueError('boolean direct mode required')
    if direct:
        return provider_pose_transform(position, rotation, None, None, True)
    inverse = invert_context_transform(tuple(parent_position[:3])+(0.,), parent_rotation)
    return provider_pose_transform(position, rotation, inverse['position'][:3]+(0.,),
                                   inverse['rotation'], False)


def prepare_application_context(basis_rows, position, reciprocal_sqrt):
    """Application caller's forward context, including its literal zero W lane.

    Unlike gathering, this caller does not invert the transform or replace zero
    scale with one. This distinction must survive composition with the helper.
    """
    from reference.ground_response_pose import entity_pose_transform
    from reference.snow import f32
    q = entity_pose_transform(basis_rows, position, 0.)['rotation']
    squares = tuple(f32(x*x) for x in q)
    n = f32(f32(squares[0]+squares[2])+f32(squares[1]+squares[3]))
    seed = f32(reciprocal_sqrt(n))
    factor = f32(f32(.5*seed)*f32(3.-f32(f32(seed*n)*seed)))
    return dict(position=tuple(map(f32,position[:3]))+(0.,),
                rotation=tuple(f32(x*factor) for x in q))
