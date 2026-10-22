"""Bounded read-only animation sampling through an already loaded host.

No stepping, input, writes or process launch. Responses remain sequential,
not atomic observations of pose and physics together.
"""
import time


def capture_animation(client, key=743623600, samples=12, interval=.1):
    if type(samples) is not int or not 1 <= samples <= 32:
        raise ValueError('samples must be 1..32')
    if type(key) is not int or not 0 <= key <= 0xffffffff:
        raise ValueError('key must be uint32')
    if not 0 <= interval <= 1:
        raise ValueError('interval must be 0..1 seconds')
    rows=[]
    started=time.monotonic()
    for index in range(samples):
        if index: time.sleep(interval)
        begin=time.monotonic()
        wall_begin=time.time_ns()
        player=client.request('player.get')
        pose=client.request('animation.get_channel',key=key)
        player_after=client.request('player.get')
        end=time.monotonic()
        rows.append(dict(index=index,elapsed_seconds=end-started,
                         request_span_seconds=end-begin,wall_begin_ns=wall_begin,wall_end_ns=time.time_ns(),
                         player=player,animation=pose,player_after=player_after))
    accepted=[row for row in rows if row['animation'].get('status')=='completed']
    found=[row for row in accepted if row['animation']['result'].get('found')]
    paired=[row for row in found if row['player'].get('status')=='completed' and
            row['player_after'].get('status')=='completed' and
            row['player']['result'].get('identity')==row['animation']['result'].get('identity')==
            row['player_after']['result'].get('identity')]
    return dict(schema='animation-host-capture-v2',rows=rows,
                accepted_queries=len(accepted),found_queries=len(found),
                matching_player_identity_queries=len(paired),
                ok=bool(paired),atomic_snapshot=False,
                animation_completion_established=False,animation_writes=False,
                distinct_epochs=len({row['animation']['result']['epoch'] for row in found}))


def summarize_animation(capture):
    """Aggregate sequential samples; never infer clip labels or input causality."""
    import math
    valid=[]
    for row in capture['rows']:
        before,pose,after=(row[k] for k in ('player','animation','player_after'))
        if any(x.get('status')!='completed' for x in (before,pose,after)):continue
        b,p,a=(x['result'] for x in (before,pose,after))
        if not p.get('found') or b.get('identity')!=p.get('identity') or a.get('identity')!=p.get('identity'):continue
        valid.append((row,b,p))
    distances=[];angles=[];body_distances=[]
    for (r0,b0,p0),(r1,b1,p1) in zip(valid,valid[1:]):
        if r1['index']!=r0['index']+1 or p0['identity']!=p1['identity']:continue
        distances.append(math.dist(p0['vector'][:3],p1['vector'][:3]))
        body_distances.append(math.dist(b0['position'],b1['position']))
        q0,q1=p0['rotation'],p1['rotation']
        n0=math.sqrt(sum(x*x for x in q0));n1=math.sqrt(sum(x*x for x in q1))
        if n0>0 and n1>0:
            dot=sum(x*y for x,y in zip(q0,q1))/(n0*n1)
            angles.append(2*math.acos(min(1,abs(dot))))
    speeds=[math.sqrt(sum(x*x for x in b['linear_velocity'])) for _,b,_ in valid]
    return dict(valid_identity_brackets=len(valid),adjacent_same_identity_pairs=len(distances),
                distinct_epochs=len({p['epoch'] for _,_,p in valid}),
                max_local_vector_delta=max(distances,default=None),
                max_local_rotation_delta_radians=max(angles,default=None),
                max_body_position_delta=max(body_distances,default=None),
                min_body_speed=min(speeds,default=None),max_body_speed=max(speeds,default=None),
                max_request_span_seconds=max((r['request_span_seconds'] for r,_,_ in valid),default=None),
                units='stored engine units; rotation delta derived from normalized quaternions',
                input_causality_established=False)
