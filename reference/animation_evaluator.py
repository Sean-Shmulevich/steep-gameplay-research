"""Independent finite-input evaluator using recovered request and gather kernels.

Evidence: CENTRAL_IMPULSE.md, Evaluator work replacement.
Existing work/bank storage is supplied. Allocation, reference ownership and
indirect context acquisition remain external services, not simulated guarantees.
"""
import struct
import math
from reference.animation_request import arbitrate_request
from reference.animation_work import gather_work_transforms, gather_raw_context_work
from reference.snow import f32


def evaluate_work_request(work, scalar, context_token, records, indices,
                          parent_position, parent_rotation, direct,
                          resolve_context, reciprocal_sqrt):
    scalar=f32(scalar)
    if not math.isfinite(scalar):
        raise ValueError('finite incoming scalar required by adapter')
    bits=lambda x:struct.unpack('<I',struct.pack('<f',f32(x)))[0]
    arbitration=arbitrate_request(work['count'],work['saved_flag'],
        work['saved_scalar_bits'],work['saved_context_token'],bits(scalar),context_token)
    result=dict(work)
    result.update(count=arbitration['work_count'],saved_flag=arbitration['saved_flag'],
        saved_scalar_bits=arbitration['saved_scalar'],saved_context_token=arbitration['saved_context'])
    if arbitration['action']=='deferred':
        return dict(action='deferred',work=result,context_resolution_requested=False)
    duration=struct.unpack('<f',struct.pack('<I',arbitration['effective_scalar']))[0]
    if not math.isfinite(duration):
        raise ValueError('finite effective duration required by adapter')
    if duration<0 or abs(duration)<=f32(1e-5):
        result.update(count=0,elapsed=0.,duration=0.)
        return dict(action='cleared',work=result,context_resolution_requested=False)
    context=resolve_context(arbitration['effective_context'])
    if context is None:
        gathered=gather_work_transforms(records,indices,parent_position,parent_rotation,direct)
    else:
        gathered=gather_raw_context_work(records,indices,parent_position,parent_rotation,direct,
            context['basis_rows'],context['position'],reciprocal_sqrt)
    result.update(records=[(r['position'],r['rotation']) for r in gathered],
        count=len(gathered),duration=duration,elapsed=0.,
        active_context_token=arbitration['effective_context'])
    return dict(action='replaced',work=result,context_resolution_requested=True)


def finish_work_update(update, prior_work, indices, parent_position, parent_rotation,
                       direct, resolve_context, reciprocal_sqrt):
    """Complete a validated update's deferred dispatch using its resulting bank.

    The update result remains a pre-handoff receipt. Returned work describes the
    post-evaluator state; ownership and allocation are still external.
    """
    work=dict(prior_work)
    work.update(count=update['clock']['count'],elapsed=update['clock']['elapsed'],
                duration=update['clock']['duration'])
    if not update['handoff']:
        return dict(action='no_handoff',work=work,context_resolution_requested=False)
    return evaluate_work_request(work,0.,0,update['records'],indices,
        parent_position,parent_rotation,direct,resolve_context,reciprocal_sqrt)
