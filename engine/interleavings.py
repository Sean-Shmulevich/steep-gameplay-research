"""Bounded exhaustive exploration of symbolic ordinary-worker interleavings.

No native timing, OS threads, injected callbacks or execution within a receiver
body. Each branch replays from fresh state, avoiding mid-callback cloning.
"""
from .mixed_scheduler import MixedScheduler


def explore(definitions, queue_policy, roots, *, max_nodes=2000, max_depth=64):
    if type(max_nodes) is not int or not 1 <= max_nodes <= 10000:
        raise ValueError('node bound must be 1..10000')
    if type(max_depth) is not int or not 1 <= max_depth <= 128:
        raise ValueError('depth bound must be 1..128')
    if not isinstance(definitions, list) or any('handler' in d or 'predicate' in d for d in definitions):
        raise ValueError('exploration requires symbolic jobs without external callbacks')
    if not isinstance(queue_policy, dict) or 'worker_slots' not in queue_policy:
        raise ValueError('explicit worker topology required')
    if not isinstance(roots, list) or any(type(n) is not str for n in roots) or len(set(roots)) != len(roots):
        raise ValueError('unique root job IDs required')
    kinds = {d['id']:d['kind'] for d in definitions}
    workers = [i for i,present in enumerate(queue_policy['worker_slots']) if present]

    def replay(path):
        model = MixedScheduler(definitions, queue_policy=queue_policy, trace_capacity=100000)
        for root in roots:model.submit(root)
        tokens, claims = {}, {}
        for worker, action in path:
            if action == 'reserve':tokens[worker] = model.reserve(worker_index=worker)
            elif action == 'claim':claims[worker] = model.claim_range(tokens[worker])
            elif action == 'range':model.execute_range(tokens[worker], claims.pop(worker))
            elif action == 'callback':model.execute_callback(tokens[worker])
            else:model.finish_dispatch(tokens.pop(worker))
        return model

    # Validate even before the first branch is expanded.
    replay([])
    pending = [[]]
    result = dict(scope='symbolic ordinary-worker API boundaries; no native concurrency proof',
                  complete=False, nodes=0, quiescent_leaves=0, blocked_leaves=0,
                  depth_cutoffs=0, pending_paths=0, violations=[], examples=[])
    while pending and result['nodes'] < max_nodes:
        path = pending.pop()
        model = replay(path)
        snapshot = model.snapshot()
        result['nodes'] += 1
        dispatches = list(snapshot['dispatches'].values())
        errors = []
        for name,job in snapshot['jobs'].items():
            active = sum(d['job']==name for d in dispatches)
            if job['executions'] != active or job['outstanding_dispatches'] != active:
                errors.append(dict(job=name, issue='dispatch/accounting mismatch'))
            if job['remaining'] < 0:
                errors.append(dict(job=name, issue='negative receiver count'))
        for name, job in snapshot['jobs'].items():
            incoming = sum(deps['successors'].count(name)
                for branches in snapshot['lists'].values() for deps in branches.values() if deps['active'])
            if job['holds'] != incoming:
                errors.append(dict(job=name, issue='dependency hold conservation failed'))
        claimed, returned, trace_executions = {}, {}, {}
        for event in snapshot['trace']['records']:
            if event['kind'] in ('mixed_dispatch_reserved', 'mixed_execution_returned'):
                trace_executions[event['job']] = event['executions']
            if event['kind'] == 'mixed_normal_list_cleared' and trace_executions.get(event['owner'],0) > 0:
                errors.append(dict(job=event['owner'], issue='dependencies released before worker return'))
            if event['kind'] == 'mixed_range_claimed':
                name = event['job']
                indices = set(range(event['start'], event['start'] + event['count']))
                seen = claimed.setdefault(name, set())
                if seen & indices or not indices <= set(range(len(snapshot['jobs'][name]['receivers']))):
                    errors.append(dict(job=name, issue='overlapping or out-of-bounds claim'))
                seen.update(indices)
            elif event['kind'] == 'mixed_receiver_return':
                name, index = event['job'], event['receiver_index']
                seen = returned.setdefault(name, set())
                if index in seen or index not in claimed.get(name, set()):
                    errors.append(dict(job=name, issue='duplicate or unclaimed receiver return'))
                seen.add(index)
        for name, job in snapshot['jobs'].items():
            if kinds[name] == 'range' and job['remaining'] + len(claimed.get(name, set())) != len(job['receivers']):
                errors.append(dict(job=name, issue='receiver claim conservation failed'))
        owners = [d['worker_index'] for d in dispatches]
        if len(set(owners)) != len(owners):errors.append(dict(issue='multiple dispatches on one worker'))
        if errors:
            result['violations'].append(dict(path=path, errors=errors))
            continue
        enabled = []
        for worker in workers:
            dispatch = next((d for d in dispatches if d['worker_index']==worker), None)
            if dispatch is None:
                if model.ready(worker_index=worker):enabled.append((worker,'reserve'))
            elif kinds[dispatch['job']] == 'callback':
                enabled.append((worker,'finish' if dispatch['callback_ran'] else 'callback'))
            elif dispatch['range'] is not None:
                enabled.append((worker,'range'))
            else:
                enabled.append((worker,'claim' if snapshot['jobs'][dispatch['job']]['remaining'] > 0 else 'finish'))
        if not enabled:
            quiet = (not dispatches
                and all(j['state']=='UNSCHEDULED' and j['holds']==0 and not j['deferred'] for j in snapshot['jobs'].values())
                and not any(d['active'] for branches in snapshot['lists'].values() for d in branches.values()))
            result['quiescent_leaves' if quiet else 'blocked_leaves'] += 1
            if len(result['examples']) < 4:
                result['examples'].append(dict(path=path, quiescent=quiet))
        elif len(path) >= max_depth:
            result['depth_cutoffs'] += 1
        else:
            pending.extend(path+[action] for action in reversed(enabled))
    result['pending_paths'] = len(pending)
    result['complete'] = not pending and not result['depth_cutoffs'] and not result['violations']
    result['status'] = 'violation' if result['violations'] else 'complete' if result['complete'] else 'bounded'
    return result


def main(argv=None):
    """Run a caller-supplied symbolic graph and produce a standalone JSON report."""
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--max-nodes', type=int, default=2000)
    parser.add_argument('--max-depth', type=int, default=64)
    args = parser.parse_args(argv)
    try:
        scenario = json.loads(args.scenario.read_text())
        if not isinstance(scenario, dict) or set(scenario) != {'definitions','queue_policy','roots'}:
            raise ValueError('scenario requires definitions, queue_policy and roots only')
        report = explore(**scenario, max_nodes=args.max_nodes, max_depth=args.max_depth)
        text = json.dumps(report, indent=2) + '\n'
        if args.output:
            if args.output.resolve() == args.scenario.resolve():
                raise ValueError('report output must not overwrite scenario')
            args.output.write_text(text)
        else:
            print(text, end='')
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, 'Experiment error: ' + str(error) + '\n')
    return 3 if report['violations'] else 0 if report['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
