"""Explicit producer/evaluator timeline; not a model of native scheduling.

Evidence: INPUT_TO_ACTION_ROUTE.md, Producer and action freshness probe.
Events choose when history updates and when action evaluation occurs. Independent
sequence counters are inspection metadata, not recovered native generations.
"""
import struct
from .action_sample import f32
from .action_history_curve import history_curve_config, evaluate_history_curve, initial_history_snapshot
from .action_history_features import update_mode3_history
from .action_history_action import evaluate_history_action


def inspect_history_action(events, *, channel, alternate_center, primary, secondary,
                           reference, direction_kind, magnitude_threshold,
                           mode, hold_delay, repeat_delay):
    """Run explicit update/evaluate events and return JSON-compatible observations.

    update: {kind, vector:[x,y,z,w], now:uint64}
    evaluate: {kind, clocks:[uint64,...], ownership:[bool,bool]}
    Each evaluate event must supply exactly the clock reads its selected branch
    consumes. Clock domains remain separate and have no assumed common epoch.
    """
    config=history_curve_config(channel,alternate_center=alternate_center)
    history=initial_history_snapshot(channel,alternate_center=alternate_center)
    action=bytes(0xe0)
    generation=0
    last_seen=None
    rows=[]
    for event in events:
        if event['kind']=='update':
            vector=event['vector']
            if not isinstance(vector,(list,tuple)) or len(vector)!=4:
                raise ValueError('update needs four finite lanes')
            raw=struct.pack('<4f',*[f32(v) for v in vector])
            history=update_mode3_history(history,raw,now=event['now'],
                primary=primary,secondary=secondary,
                curve=lambda x:evaluate_history_curve(x,config['points']))['snapshot']
            generation+=1
            rows.append(dict(kind='update',producer_sequence=generation,
                             history_timestamp=event['now']))
        elif event['kind']=='evaluate':
            clocks=iter(event['clocks'])
            gates=iter(event['ownership'])
            def clock():
                try:return next(clocks)
                except StopIteration:raise ValueError('missing action clock read') from None
            def blocked():
                try:return next(gates)
                except StopIteration:raise ValueError('missing ownership observation') from None
            result=evaluate_history_action(action,history,reference,
                direction_kind=direction_kind,magnitude_threshold=magnitude_threshold,
                mode=mode,hold_delay=hold_delay,repeat_delay=repeat_delay,
                ownership_blocked=blocked,read_clock=clock)
            sentinel=object()
            if next(clocks,sentinel) is not sentinel or next(gates,sentinel) is not sentinel:
                raise ValueError('unused clock or ownership observations')
            action=result['snapshot']
            rows.append(dict(kind='evaluate',producer_sequence=generation,
                producer_ran=generation>0,reused_history=last_seen==generation,
                history_timestamp=struct.unpack_from('<Q',history)[0],
                active=result['timing']['active'],magnitude=result['magnitude'],
                start_time=result['timing']['start_time'],repeat_time=result['timing']['repeat_time'],
                clock_reads=result['timing']['clock_reads']))
            last_seen=generation
        else:
            raise ValueError('event kind must be update or evaluate')
    return dict(game_process=False,scope='Explicit synthetic timeline; native scheduling not inferred',
                sequence_policy='Producer counters are inspection metadata',observations=rows)
