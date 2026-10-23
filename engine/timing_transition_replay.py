"""Replay a qualified single history append, not infer cadence from durations.

Evidence: SCHEDULER_SMOOTHING_AUDIT.md. Snapshot matching and acceptance rules
are authored analysis. Equal outputs alone cannot establish one producer call.
"""
import struct
from .scheduler import schedule


def replay_timing_transition(before, after):
    """Input: two observed timing dictionaries from physics_timing_observation.

    Accept only unchanged ownership/configuration and an exact single ring append.
    Full-ring cycles or unrelated writers can alias this condition; acceptance
    is a consistency result, not proof of execution count or exclusive ownership.
    """
    identities=('owner','physics_manager','world','history_pointer')
    config=('smoothing_enabled','policy','history_capacity')
    if any(before[k]!=after[k] for k in identities):
        return dict(status='identity_changed')
    if any(before[k]!=after[k] for k in config):
        return dict(status='configuration_changed')
    if not before['smoothing_enabled'] or not 0<before['history_capacity']<=64:
        return dict(status='unsupported_configuration')
    capacity=before['history_capacity'];count=before['history_count'];write=before['history_write'];oldest=before['history_oldest']
    if (not 0<=count<=capacity or not 0<=write<capacity or not 0<=oldest<capacity
            or write!=(oldest+count)%capacity
            or len(before['history_bits'])!=capacity or len(after['history_bits'])!=capacity):
        raise ValueError('invalid observed ring')
    expected_count=min(count+1,capacity)
    expected_oldest=(oldest+(count==capacity))%capacity
    expected_write=(write+1)%capacity
    cursor_match=(after['history_count'],after['history_write'],after['history_oldest'])==(expected_count,expected_write,expected_oldest)
    unchanged=all(before['history_bits'][i]==after['history_bits'][i] for i in range(capacity) if i!=write)
    if not cursor_match or not unchanged:
        return dict(status='not_single_append',cursor_matches=cursor_match,
                    untouched_slots_match=unchanged,
                    cursor_delta_mod_capacity=(after['history_write']-write)%capacity)
    f=lambda bits:struct.unpack('<f',struct.pack('<I',bits))[0]
    bits=lambda value:struct.unpack('<I',struct.pack('<f',value))[0]
    active={(oldest+i)%capacity for i in range(count)}
    # Unused allocation bits are not inputs to the moving mean.
    values=[f(x) if i in active else 0.0 for i,x in enumerate(before['history_bits'])]
    incoming=f(after['history_bits'][write])
    state=dict(mode='subdivision',retained=before['retained'],history=dict(
        capacity=capacity,values=values,count=count,write=write,oldest=oldest))
    schedule(state,incoming,dict(mode='subdivision',smoothing_enabled=True,
                                policy=before['policy'],history_capacity=capacity))
    expected=dict(retained=state['retained'],consumed=state['last_consumed'],
                  inverse_consumed=state['inverse_consumed_dt'],frequency=state['selected_frequency'],
                  elapsed=state['last_elapsed'])
    mismatches=[key for key,value in expected.items() if bits(value)!=bits(after[key])]
    if state['last_count']!=after['step_count']:mismatches.append('step_count')
    return dict(status='compared',matches=not mismatches,mismatched_fields=mismatches,
                incoming_from_history=incoming,branch=state['last_plan']['branch'],
                producer_call_count_proved=False)
