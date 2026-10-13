"""Synthetic three-cycle mixed scheduler probe; no game or asset dependency.

Run from repository root: python3 -m engine.examples.mixed_scheduler_probe
The topology illustrates recovered job semantics, not the full native graph.
"""
import json

from engine.mixed_scheduler import MixedScheduler


def run_probe():
    context = {'cycle': 0, 'ends': [], 'receivers': [], 'resubmission': []}

    def root_body(ctx, receiver):
        ctx['cycle'] += 1
        ctx['scheduler'].prepare_range('motion', ['rider', 'other'])

    def select_motion(ctx):
        return ctx['cycle'] != 2

    def motion_body(ctx, receiver):
        ctx['receivers'].append({'cycle': ctx['cycle'], 'receiver': receiver})

    def end_body(ctx, receiver):
        ctx['ends'].append(ctx['cycle'])
        if ctx['cycle'] < 3:
            before = ctx['scheduler'].snapshot()
            ctx['scheduler'].submit('root', context=ctx)
            after = ctx['scheduler'].snapshot()
            end = before['jobs']['end']
            assert end['state'] == 'DONE' and end['executions'] == end['outstanding_dispatches'] == 1
            assert after['jobs']['root']['state'] == 'SCHEDULED'
            ctx['resubmission'].append({
                'cycle': ctx['cycle'],
                'end_state': end['state'],
                'end_executions': end['executions'],
                'end_outstanding_dispatches': end['outstanding_dispatches'],
                'next_root_state': after['jobs']['root']['state'],
            })

    handlers = {name: {'version': 'synthetic-v1', 'callback': callback}
                for name, callback in [('root_body', root_body), ('select_motion', select_motion),
                                       ('motion_body', motion_body), ('end_body', end_body)]}
    definitions = [
        {'id': 'root', 'kind': 'callback', 'handler': 'root_body', 'successors': ['route']},
        {'id': 'route', 'kind': 'conditional', 'predicate': 'select_motion',
         'successors': ['motion'], 'secondary': ['bypass']},
        {'id': 'motion', 'kind': 'range', 'handler': 'motion_body', 'receivers': [],
         'successors': ['join']},
        {'id': 'bypass', 'kind': 'terminal', 'successors': ['join']},
        {'id': 'join', 'kind': 'terminal', 'successors': ['end']},
        {'id': 'end', 'kind': 'callback', 'handler': 'end_body'},
    ]
    scheduler = MixedScheduler(definitions, handlers, trace_capacity=4096)
    context['scheduler'] = scheduler
    scheduler.submit('root', context=context)
    scheduler.run_ready(context=context, max_dispatches=50)
    assert context['ends'] == [1, 2, 3], context['ends']
    assert sorted(row['cycle'] for row in context['receivers']) == [1, 1, 3, 3]
    assert scheduler.snapshot()['trace']['complete']
    assert not scheduler.snapshot()['dispatches']
    return {
        'scope': 'Synthetic topology using recovered local scheduler rules; not a native trace',
        'completed_cycles': context['ends'],
        'receiver_visits': context['receivers'],
        'resubmission_observations': context['resubmission'],
        'final': scheduler.snapshot(),
    }


if __name__ == '__main__':
    print(json.dumps(run_probe(), indent=2))
