"""Recovered ragdoll dependency subset with synthetic ranges and no-op bodies."""
import json
from pathlib import Path
from engine.mixed_scheduler import MixedScheduler

BRANCHES = ('SkeletonUpdateForRagdoll', 'SkeletonUpdateForRagdollInteractions')
JOIN = 'PhysicForRagdollUpdate'


def run_probe(delayed_branch=BRANCHES[1]):
    """Keep a claimed range unfinished; distinguish body and dispatch completion.

    The interaction visitor's entries represent batches, unlike ordinary receiver
    entries. Their contents are deliberately synthetic and are not evaluated.
    """
    if delayed_branch not in BRANCHES:
        raise ValueError('expected a skeleton-update branch')
    definitions = json.loads(Path(__file__).with_name('ragdoll_stage_graph.json').read_text())
    for job in definitions:
        job['receivers'] = ['synthetic-entry']
    scheduler = MixedScheduler(definitions)
    observations = []

    def observe(stage):
        jobs = scheduler.snapshot()['jobs']
        observations.append(dict(stage=stage, join_holds=jobs[JOIN]['holds'],
            join_started=jobs[JOIN]['started'],
            delayed_remaining=jobs[delayed_branch]['remaining'],
            delayed_executions=jobs[delayed_branch]['executions']))

    def finish(name):
        token = scheduler.reserve(name)
        while (span := scheduler.claim_range(token)) is not None:
            scheduler.execute_range(token, span)
        scheduler.finish_dispatch(token)

    scheduler.submit('SkelUpdateEndAnimateRagdoll')
    finish('SkelUpdateEndAnimateRagdoll')
    observe('both branches pending')
    finish(next(name for name in BRANCHES if name != delayed_branch))
    observe('other branch finished')
    token = scheduler.reserve(delayed_branch)
    span = scheduler.claim_range(token)
    observe('delayed range claimed')
    scheduler.execute_range(token, span)
    observe('delayed body returned')
    scheduler.finish_dispatch(token)
    observe('delayed dispatch finished')
    finish(JOIN)
    observe('join finished')
    return dict(scope='Recovered partial dependency topology; synthetic range entries and no-op bodies. Not native dispatch, live membership or a safe snapshot fence.',
                delayed_branch=delayed_branch, observations=observations,
                trace=scheduler.snapshot()['trace'])


if __name__ == '__main__':
    print(json.dumps(run_probe(), indent=2))
