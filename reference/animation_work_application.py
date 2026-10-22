"""Recovered context-free work application loop.

Evidence: CENTRAL_IMPULSE.md, Context-free work application loop.
Clock, initial dirty-bit clear, context resolution and request handoff excluded.
"""
from reference.animation_work import gather_work_transforms, encode_work_pose
from reference.animation_work_rotation import blend_work_rotation
from reference.snow import f32


def apply_work_records(records, indices, saved, parent_position, parent_rotation,
                       direct, elapsed, duration, reciprocal_sqrt, acos, sin):
    records = [(tuple(p), tuple(q)) for p, q in records]
    indices, saved = list(indices), list(saved)
    if len(indices) != len(saved):
        return dict(records=records, written=False, branches=[], action='count_mismatch')
    duration = f32(duration)
    if duration == 0:
        raise ValueError('nonzero duration required by inspection adapter')
    alpha = f32(f32(elapsed) / duration)
    branches = []
    for index, (position, rotation) in zip(indices, saved):
        # Duplicate indices observe preceding writes, not the initial bank.
        current = gather_work_transforms(records, [index], parent_position,
                                         parent_rotation, direct)[0]
        blended = blend_work_rotation(rotation, current['rotation'], alpha,
                                      reciprocal_sqrt, acos, sin)
        position = tuple(f32(f32(a) + f32(f32(b-f32(a))*alpha))
                         for a,b in zip(position,current['position']))
        encoded = encode_work_pose(position, blended['rotation'], parent_position,
                                   parent_rotation, direct)
        records[index] = (encoded['position'], encoded['rotation'])
        branches.append(blended['branch'])
    return dict(records=records, written=bool(indices), branches=branches, action='applied')


def update_context_free_work(records, indices, saved, parent_position, parent_rotation,
                             direct, elapsed, duration, dt, bank_flags, saved_flag,
                             bank_present, reciprocal_sqrt, acos, sin):
    """Context-free update through deferred evaluator dispatch, before its effects.

    dt is already selected from the entity's world timing group. A returned
    handoff requests the evaluator; this function does not fabricate its effects.
    """
    from reference.animation_work_timing import advance_work_clock, saved_request_handoff
    if type(bank_flags) is not int or not 0 <= bank_flags <= 0xffffffff:
        raise ValueError('uint32 bank flags required')
    saved = list(saved)
    clock = advance_work_clock(elapsed, duration, dt, len(saved), bank_present)
    result = dict(records=[(tuple(p),tuple(q)) for p,q in records], written=False,
                  branches=[], action=clock['action'], clock=clock,
                  bank_flags=bank_flags, handoff=False)
    if clock['action'] != 'apply':
        return result
    result.update(apply_work_records(records, indices, saved, parent_position,
        parent_rotation, direct, clock['elapsed'], clock['duration'],
        reciprocal_sqrt, acos, sin))
    result['bank_flags'] = (bank_flags & ~(1 << 27)) | ((1 << 27) if result['written'] else 0)
    result['handoff'] = saved_request_handoff(saved_flag)['invoke']
    return result


def update_context_work(records, indices, saved, parent_position, parent_rotation,
                        direct, elapsed, duration, dt, bank_flags, saved_flag,
                        bank_present, basis_rows, context_position,
                        reciprocal_sqrt, acos, sin):
    """Context-bearing update to the deferred-dispatch boundary.

    Matrix comes from an external context accessor. Acquisition and lifetime are
    outside this independent operation. Numerical services are explicit.
    """
    from reference.animation_work import prepare_application_context, gather_context_work
    from reference.animation_work_timing import advance_work_clock, saved_request_handoff
    saved, indices = list(saved), list(indices)
    records = [(tuple(p), tuple(q)) for p,q in records]
    clock = advance_work_clock(elapsed, duration, dt, len(saved), bank_present)
    result = dict(records=records, written=False, branches=[], action=clock['action'],
                  clock=clock, bank_flags=bank_flags, handoff=False)
    if clock['action'] != 'apply':
        return result
    result['bank_flags'] &= ~(1 << 27)
    context = prepare_application_context(basis_rows, context_position, reciprocal_sqrt)
    if len(indices) != len(saved):
        result['action'] = 'count_mismatch'
    else:
        result['action'] = 'applied'
        for index, record in zip(indices, saved):
            # Native normalization is interleaved with each read/blend/write.
            converted = gather_context_work([record], [0], None, None, True,
                context['position'], context['rotation'], reciprocal_sqrt)[0]
            applied = apply_work_records(result['records'], [index],
                [(converted['position'], converted['rotation'])],
                parent_position, parent_rotation, direct, clock['elapsed'],
                clock['duration'], reciprocal_sqrt, acos, sin)
            result['records'] = applied['records']
            result['branches'].extend(applied['branches'])
            result['written'] = True
            result['bank_flags'] |= 1 << 27
    result['handoff'] = saved_request_handoff(saved_flag)['invoke']
    return result
