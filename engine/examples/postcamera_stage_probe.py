"""Two recovered post-camera completion joins; synthetic data only."""
import json
from pathlib import Path
from engine.mixed_scheduler import MixedScheduler

BRANCHES = ('SkeletonUpdate', 'RagdollAfterCamera', 'SkeletonUpdateInteractions')
FOLLOWERS = ('KinoAfterSkeleton', 'KinoAfterSkeletonHiPriority', 'KinoAfterSkeletonWithInteractions')
JOIN = 'LiteRagdollUpdate'


def run_probe(delayed_branch='RagdollAfterCamera', delayed_follower=FOLLOWERS[0]):
    if delayed_branch not in BRANCHES or delayed_follower not in FOLLOWERS:
        raise ValueError('expected a registered branch and follower')
    definitions = json.loads(Path(__file__).with_name('postcamera_stage_graph.json').read_text())
    for job in definitions:
        if job['kind'] == 'range':
            job['receivers'] = ['synthetic-entry']
    scheduler = MixedScheduler(definitions)
    observations = []

    def observe(stage):
        jobs = scheduler.snapshot()['jobs']
        observations.append(dict(stage=stage, follower_holds={n: jobs[n]['holds'] for n in FOLLOWERS},
            follower_started={n: jobs[n]['started'] for n in FOLLOWERS},
            join_holds=jobs[JOIN]['holds'], join_started=jobs[JOIN]['started'],
            branch_remaining=jobs[delayed_branch]['remaining'],
            branch_executions=jobs[delayed_branch]['executions']))

    def finish(name):
        token = scheduler.reserve(name)
        if name == 'SkeletonGatherComponents':
            scheduler.execute_callback(token)
        else:
            while (span := scheduler.claim_range(token)) is not None:
                scheduler.execute_range(token, span)
        scheduler.finish_dispatch(token)

    scheduler.submit('SkeletonGatherComponents')
    finish('SkeletonGatherComponents')
    observe('three branches pending')
    for branch in BRANCHES:
        if branch != delayed_branch:
            finish(branch)
    token = scheduler.reserve(delayed_branch)
    span = scheduler.claim_range(token)
    observe('last branch claimed')
    scheduler.execute_range(token, span)
    observe('last branch body returned')
    scheduler.finish_dispatch(token)
    observe('all branches finalized')
    for follower in FOLLOWERS:
        if follower != delayed_follower:
            finish(follower)
    token = scheduler.reserve(delayed_follower)
    span = scheduler.claim_range(token)
    scheduler.execute_range(token, span)
    observe('last follower body returned')
    scheduler.finish_dispatch(token)
    observe('all followers finalized')
    finish(JOIN)
    return dict(scope='Recovered partial topology with synthetic entries and no-op bodies; no live pose fence or native visitor execution.',
                observations=observations, trace=scheduler.snapshot()['trace'])


if __name__ == '__main__':
    print(json.dumps(run_probe(), indent=2))
