"""Run the recovered partial topology with synthetic bodies and receivers.

python3 -m engine.examples.animation_stage_probe
No original game attachment or native scheduling is performed.
"""
import json
from pathlib import Path
from engine.mixed_scheduler import MixedScheduler


def run_probe():
    definitions = json.loads(Path(__file__).with_name('animation_stage_graph.json').read_text())
    for job in definitions:
        if job['kind'] == 'range':
            job['receivers'] = ['synthetic-receiver']
        if job['id'] == 'AnimationUpdateTime':
            job.update(receivers=['synthetic-a', 'synthetic-b'], max_concurrency=2)
    scheduler = MixedScheduler(definitions)
    def finish(name):
        token = scheduler.reserve(name)
        kind = next(job['kind'] for job in definitions if job['id'] == name)
        if kind == 'callback':
            scheduler.execute_callback(token)
        else:
            while (span := scheduler.claim_range(token)) is not None:
                scheduler.execute_range(token, span)
        scheduler.finish_dispatch(token)

    observations = []
    def observe(stage):
        jobs = scheduler.snapshot()['jobs']
        animation = jobs['AnimationUpdateTime']
        gather = jobs['ActionGatherComponents']
        observations.append(dict(stage=stage, animation_remaining=animation['remaining'],
            animation_executions=animation['executions'], gather_holds=gather['holds'],
            gather_requested=gather['requested'], gather_started=gather['started']))

    scheduler.submit('UpdatePreActionGather')
    for name in ('UpdatePreActionGather','UpdateCharacterActionSet','SkelUpdateBeginAnimate','UpdateKino'):
        finish(name)
    observe('both branches pending')
    finish('UpdateActionKinoStatesInteraction')
    observe('interaction returned')
    tokens = [scheduler.reserve('AnimationUpdateTime') for _ in range(2)]
    spans = [scheduler.claim_range(token) for token in tokens]
    observe('all animation ranges claimed')
    for index, (token, span) in enumerate(zip(tokens, spans)):
        scheduler.execute_range(token, span)
        observe(f'animation body {index} returned before dispatch finish')
        scheduler.finish_dispatch(token)
        observe(f'animation dispatch {index} finished')
    finish('ActionGatherComponents')
    return dict(scope='Recovered partial topology; synthetic receivers, serial dispatches and no-op bodies. Not a live original-game trace.',
        observations=observations, trace=scheduler.snapshot()['trace'])


if __name__ == '__main__':
    print(json.dumps(run_probe(), indent=2))
