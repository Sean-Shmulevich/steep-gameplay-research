"""Execute the recovered skeleton wrapper with synthetic job bodies."""
import json
from pathlib import Path
from engine.mixed_scheduler import MixedScheduler


def run_probe(world_field=0):
    if type(world_field) is not int or not -2**31 <= world_field < 2**31:
        raise ValueError('signed 32-bit world field required')
    definitions = json.loads(Path(__file__).with_name('postcamera_stage_graph.json').read_text())
    bodies = []
    def record(ctx, receiver):
        bodies.append(receiver)
    for job in definitions:
        if job['kind'] == 'range':
            job['receivers'] = [job['id']]
            job['handler'] = 'record'
        if job['id'] == 'LiteRagdollUpdate':
            job['successors'] = ['UpdateSkeletonEndNode']
    definitions += [
        dict(id='UpdateSkeletonWorldIsPausedBranch', kind='conditional',
             condition=world_field <= 0, successors=['SkeletonGatherComponents'],
             secondary=['UpdateSkeletonEndNode']),
        dict(id='UpdateSkeletonEndNode', kind='terminal'),
    ]
    scheduler = MixedScheduler(definitions, {'record': {'version': 'synthetic-v1', 'callback': record}})
    scheduler.activate('UpdateSkeletonWorldIsPausedBranch')
    scheduler.submit('UpdateSkeletonWorldIsPausedBranch')
    scheduler.run_ready(max_dispatches=50)
    snap = scheduler.snapshot()
    return dict(scope='Recovered local wrapper and post-camera topology; synthetic bodies. Terminal reachability does not certify a fresh native pose.',
                world_field=world_field, primary_selected=world_field <= 0,
                executed_range_jobs=bodies, jobs=snap['jobs'], trace=snap['trace'])


if __name__ == '__main__':
    print(json.dumps([run_probe(0), run_probe(1)], indent=2))
