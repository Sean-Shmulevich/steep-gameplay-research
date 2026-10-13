"""Analyze serial owned-engine evidence; no native or wall-clock timing claims."""
from .trace import Trace

PHASES = ('physics', 'environment', 'scoring', 'animation', 'camera')


def analyze(snapshot):
    """Validate a Trace snapshot and return JSON correlation and ordering evidence.

    Malformed envelopes/identifiers raise ValueError. Valid event records with
    contradictory ordering remain visible as anomalies. Missing endings remain
    unresolved, including snapshots taken while work is running.
    """
    try:
        trace = Trace.restore(snapshot)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ValueError('Invalid trace snapshot') from exc
    frames, substeps, anomalies = {}, {}, []
    def identity(row, key, nullable=False):
        value = row.get(key)
        if value is None and nullable:
            return None
        if type(value) is not int or value < 0:
            raise ValueError('Invalid '+key)
        return value
    def anomaly(row, message):
        item = dict(sequence=row['sequence'], message=message)
        anomalies.append(item)
        return item
    def frame(key):
        return frames.setdefault(key, dict(frame_invocation=key, entered=None, planned=None,
            planned_count=None, outcome='unresolved', end=None, substeps=[]))
    for row in trace.records:
        kind, seq = row['kind'], row['sequence']
        if kind in ('frame_enter','frame_planned','frame_committed','frame_aborted'):
            key = identity(row,'frame_invocation'); f = frame(key)
            if kind == 'frame_enter':
                if f['entered'] is not None:anomaly(row,'duplicate frame entry')
                if key != seq:anomaly(row,'frame identity differs from entry sequence')
                f['entered'] = seq
            else:
                if f['entered'] is None:anomaly(row,'frame event without entry')
                if f['end'] is not None:anomaly(row,'frame event after frame end')
                if kind == 'frame_planned':
                    if not isinstance(row.get('steps'),list):raise ValueError('Invalid frame steps')
                    if f['planned'] is not None:anomaly(row,'duplicate frame plan')
                    f['planned'] = seq;f['planned_count'] = len(row['steps'])
                else:
                    f['outcome'] = 'committed' if kind=='frame_committed' else 'aborted';f['end']=seq
            continue
        if kind not in ('substep_enter','substep_committed','substep_aborted','physics_complete','animation_complete','gameplay_job'):
            continue
        key = identity(row,'invocation'); fk = identity(row,'frame_invocation',True)
        s = substeps.setdefault(key, dict(invocation=key,frame_invocation=fk,entered=None,end=None,
            local_outcome='unresolved',effective_outcome='unresolved',mode='direct_or_unobserved',
            phases={name:dict(entered=[],returned=[],worker_completed=[],observed_complete=[]) for name in PHASES},
            terminal_begins=[],failures=[],anomalies=[],entry=None,ending=None))
        def issue(message):s['anomalies'].append(anomaly(row,message))
        if fk != s['frame_invocation']:issue('substep frame identity changed')
        if kind == 'substep_enter':
            if s['entered'] is not None:issue('duplicate substep entry')
            if key != seq:issue('substep identity differs from entry sequence')
            s['entered']=seq;s['entry']={key:row.get(key) for key in ('tick','elapsed_dt','derivative_dt','input_generation')}
            if fk is not None:
                f=frame(fk);f['substeps'].append(key)
                if f['planned'] is None:issue('substep entered before frame plan')
                if f['end'] is not None:issue('substep entered after frame end')
            continue
        if s['entered'] is None:issue('substep evidence without entry')
        if s['end'] is not None:issue('substep evidence after end')
        if kind in ('substep_committed','substep_aborted'):
            s['local_outcome']='committed' if kind=='substep_committed' else 'aborted';s['end']=seq
            s['ending']={key:row[key] for key in ('tick','error','state_hash') if key in row}
        elif kind in ('physics_complete','animation_complete'):
            name=kind.removesuffix('_complete');s['phases'][name]['observed_complete'].append(seq)
        else:
            s['mode']='mixed'
            event=row.get('job_event');name=row.get('job')
            if not isinstance(event,str):raise ValueError('Invalid job event')
            if event=='mixed_terminal_begin':s['terminal_begins'].append(dict(sequence=seq,job=name))
            elif event=='mixed_handler_failed':s['failures'].append(dict(sequence=seq,handler=row.get('handler'),error=row.get('type')))
            elif event in ('mixed_receiver_enter','mixed_callback_enter','mixed_receiver_return','mixed_callback_return','mixed_dispatch_accounting_returned'):
                if name not in PHASES:issue('unknown gameplay phase')
                else:
                    field = 'worker_completed' if event=='mixed_dispatch_accounting_returned' else ('entered' if event.endswith('_enter') else 'returned')
                    s['phases'][name][field].append(seq)
    for s in substeps.values():
        def issue(message):
            item=dict(sequence=s['end'] if s['end'] is not None else s['entered'],message=message)
            s['anomalies'].append(item);anomalies.append(item)
        previous=None;prior_phase=None
        for name,p in s['phases'].items():
            for field,values in p.items():
                if len(values)>1:issue('duplicate '+name+' '+field)
            if p['returned'] and (not p['entered'] or p['returned'][0]<=p['entered'][0]):issue(name+' return without prior entry')
            if p['worker_completed'] and (not p['returned'] or p['worker_completed'][0]<=p['returned'][0]):issue(name+' worker completion without prior body return')
            if p['entered']:
                if prior_phase is not None and not s['phases'][prior_phase]['returned']:issue('phase entered before previous callback returned')
                if previous is not None and p['entered'][0]<=previous:issue('phase entry order violation')
                previous=p['returned'][0] if p['returned'] else p['entered'][0]
                prior_phase=name
            if s['mode']=='mixed' and p['observed_complete'] and (not p['entered'] or p['observed_complete'][0]<=p['entered'][0] or (p['returned'] and p['observed_complete'][0]>=p['returned'][0])):issue(name+' observation outside callback body')
        physics=s['phases']['physics']['observed_complete'];animation=s['phases']['animation']['observed_complete']
        if s['mode']=='direct_or_unobserved' and physics and animation:s['mode']='direct'
        if physics and animation and physics[0]>=animation[0]:issue('animation observation precedes physics')
        if s['local_outcome']=='committed':
            if not physics or not animation:issue('commit missing numerical phase evidence')
            if s['mode']=='mixed':
                if any(not p['worker_completed'] for p in s['phases'].values()):issue('commit before all worker completions')
                if len(s['terminal_begins'])!=1 or s['terminal_begins'][0]['job']!='ready':issue('commit missing ready terminal')
            if s['failures']:issue('commit follows handler failure')
        fk=s['frame_invocation'];f=frames.get(fk)
        s['effective_outcome']=s['local_outcome']
        if f and f['outcome']=='aborted':s['effective_outcome']='rolled_back'
        elif f and f['outcome']=='unresolved' and s['local_outcome']=='committed':s['effective_outcome']='pending_frame'
        if trace.dropped and s['effective_outcome'] in ('committed','unresolved'):s['effective_outcome']='unverified_incomplete_trace'
    for f in frames.values():
        if f['outcome']=='committed':
            if f['planned_count']!=len(f['substeps']) or any(substeps[k]['local_outcome']!='committed' for k in f['substeps']):
                anomalies.append(dict(sequence=f['end'],message='frame commit disagrees with planned/committed substeps'))
        if f['end'] is not None and any(substeps[k]['end'] is None or substeps[k]['end']>=f['end'] for k in f['substeps']):
            anomalies.append(dict(sequence=f['end'],message='frame ended before entered substeps ended'))
        f['verified']=bool(not trace.dropped and f['outcome']!='unresolved' and not anomalies)
    complete=not trace.dropped
    unresolved=any(s['effective_outcome'] in ('unresolved','pending_frame','unverified_incomplete_trace') for s in substeps.values()) or any(f['outcome']=='unresolved' for f in frames.values())
    return dict(schema_version=1,complete=complete,status='incomplete' if not complete or unresolved else ('anomalous' if anomalies else 'complete'),
        counts=dict(records=len(trace.records),attempted=trace.attempted,dropped=trace.dropped,frames=len(frames),substeps=len(substeps)),
        frames=list(frames.values()),substeps=list(substeps.values()),anomalies=anomalies,
        scope='serial owned-engine event evidence; no wall-clock durations or native execution claims')
