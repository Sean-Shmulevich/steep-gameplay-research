"""Synthetic composition of recovered retirement/loading boundaries.

Run: python3 -m engine.examples.retirement_loading_probe
No native calls, resource destruction, timing, allocator or concurrency proof.
The driver deliberately chooses serial operations; those choices are authored.
"""
import json
from engine.holder_release_route import holder_release_route
from engine.holder_consumer_route import holder_consumer_route
from engine.loading_destruction import stage_increment, take_staged, publish_captured, take_pending, stop_poll_passes


def probe(*, reacquired_count=False):
    if type(reacquired_count) is not bool:
        raise ValueError('reacquired_count must be boolean')
    state = dict(holder_status=0x80000000, retirement_count=0,
                 loading_ring_count=0, staged=0, publication_captured=0,
                 pending=0, busy=0, batch_remaining=0)
    trace=[]
    def emit(boundary, calls=()):
        trace.append(dict(boundary=boundary, **state, calls=list(calls),
                          stop_poll_passes=stop_poll_passes(state['pending'],state['busy'])))
    emit('initial')
    route=holder_release_route(state['holder_status'],payload_present=True,
                               global_suppress=False,manager_mode=0,thread_kind=3)
    assert route['route']=='enqueue'
    state['holder_status']=route['status'];state['retirement_count']=1
    emit('holder_enqueued')
    if reacquired_count:
        # A supplied scenario change, not an emulated native acquisition API.
        state['holder_status']+=1
        emit('scenario_count_becomes_nonzero')
    route=holder_consumer_route(state['holder_status'],payload_present=True,manager_mode=0)
    state['retirement_count']=0;state['holder_status']=route['status']
    if 'dispatch_payload' in route['events']:
        state['loading_ring_count']+=1
        state['staged']=stage_increment(state['staged'])
    emit('retirement_item_consumed',route['events'])
    transfer=take_staged(state['staged'])
    state['staged']=transfer['staged'];state['publication_captured']=transfer['captured']
    emit('staged_count_captured')
    published=publish_captured(state['pending'],state['publication_captured'])
    state['pending']=published['pending'];state['publication_captured']=0
    emit('count_published',['notify_loading_worker'] if published['notify_worker'] else [])
    state['busy']=1;emit('loading_busy_set')
    batch=take_pending(state['pending']);state['pending']=batch['pending'];state['batch_remaining']=batch['iterations']
    emit('loading_batch_captured')
    while state['batch_remaining']:
        # Valid populated ring is a scenario precondition, not a fallback for
        # the native retained-pointer-on-empty behavior documented separately.
        if state['loading_ring_count']<=0:
            raise ValueError('outside probe scope: pending/ring mismatch')
        state['loading_ring_count']-=1;state['batch_remaining']-=1
        emit('loading_item_consumed',['virtual_destructor_requested','allocation_release_requested'])
    state['busy']=0;emit('loading_busy_cleared')
    return dict(evidence='Synthetic serial composition of locally reconstructed rules',
                native_execution=False,disposal_proved=False,callback_drain_proved=False,
                assumptions=['One synthetic holder with payload; mode zero; sufficient capacity.',
                             'No callback mutations, new submissions or exceptions.',
                             'Destructor and free are recorded requests, not executed.'],trace=trace)


if __name__ == '__main__':
    print(json.dumps(probe(),indent=2))
