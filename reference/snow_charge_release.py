"""Recovered release-state branch with caller-supplied remapped/cooked input.

See docs/systems/snow/integration/CLIENT_GUIDE.txt, 'Saved charge and release
signal'. Device remapping, cooker and update-mode selection remain external.
Finite validation and positive derivative interval are authored API policy.
"""
from reference.central_impulse import f32


def update_release(state, *, new_cooked, raw_remapped_charge, elapsed_dt,
                   derivative_dt, release_threshold, input_update_mode):
    fields=('cooked','saved_charge','elapsed','rate','release_signal','release_copy')
    result={key:f32(state[key]) for key in fields}
    new_cooked,raw,dt,derivative,threshold=map(f32,(new_cooked,raw_remapped_charge,elapsed_dt,derivative_dt,release_threshold))
    if dt < 0 or derivative <= 0 or threshold < 0 or type(input_update_mode) is not int:
        raise ValueError('Nonnegative elapsed/threshold, positive derivative and integer mode required')
    previous=result['cooked']; result['cooked']=new_cooked
    result['elapsed']=f32(result['elapsed']+dt)
    if input_update_mode != 1:
        return result
    result['release_signal']=result['release_copy']=0.
    result['rate']=f32(f32(new_cooked-previous)/derivative)
    saved=result['saved_charge']
    if saved != 0 and new_cooked == 0:
        if result['elapsed'] < threshold:
            result['release_signal']=result['release_copy']=saved
        result['saved_charge']=0.
    elif raw >= saved or (result['rate'] != 0 and result['rate'] > -1):
        result['saved_charge']=raw
        result['elapsed']=0.
    return result
