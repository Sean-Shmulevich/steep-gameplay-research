"""Compare empty ranges and callback execution on the recovered partial graph.

python3 -m engine.examples.scheduler_begin_probe
Synthetic empty populations; not a claim about the live game's population.
"""
import json
from pathlib import Path
from engine.mixed_scheduler import MixedScheduler


def run_probe():
    definitions = json.loads(Path(__file__).with_name('animation_stage_graph.json').read_text())
    body_observations = []
    handlers = {}

    def callback(name):
        def body(context, receiver):
            job = scheduler.snapshot()['jobs'][name]
            body_observations.append(dict(job=name, executions=job['executions'],
                                          outstanding_dispatches=job['outstanding_dispatches']))
        return body

    for spec in definitions:
        if spec['kind'] == 'range':
            spec['receivers'] = []
        else:
            spec['handler'] = spec['id']
            handlers[spec['id']] = dict(version='synthetic-observer-v1', callback=callback(spec['id']))
    scheduler = MixedScheduler(definitions, handlers)
    boundary_observations = []

    def observe(label):
        snapshot = scheduler.snapshot()
        boundary_observations.append(dict(stage=label, queue=snapshot['queue'],
            jobs={name: {key: row[key] for key in ('state', 'requested', 'started',
                  'holds', 'remaining', 'executions', 'outstanding_dispatches')}
                  for name, row in snapshot['jobs'].items()}))

    scheduler.submit('UpdatePreActionGather')
    observe('root submitted')
    for name in ('UpdatePreActionGather', 'UpdateKino', 'ActionGatherComponents'):
        token = scheduler.reserve(name)
        scheduler.execute_callback(token)
        scheduler.finish_dispatch(token)
        observe(name + ' finished')
    return dict(scope='Recovered partial graph with deliberately empty synthetic range populations; serial adapter execution, not a native trace.',
                boundary_observations=boundary_observations,
                callback_observations=body_observations,
                trace=scheduler.snapshot()['trace'])


if __name__ == '__main__':
    print(json.dumps(run_probe(), indent=2))
