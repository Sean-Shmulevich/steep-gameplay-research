"""Caller-ordered producer/consumer inspection, not a recovered scheduler.

Contract: CENTRAL_IMPULSE.md, Ordered markup-to-body inspection.
"""
from copy import deepcopy
import argparse
import json
from pathlib import Path
from .markup_vector_bench import inspect as inspect_producer
from reference.central_impulse import consume_pending_impulse, f32
from .snow_post_pending import directional_submissions, summed_submissions
from .point_impulse import apply_point_impulse, world_inverse_inertia


def inspect(document):
    if document.get('schema') != 'markup-motion-sequence-v1':
        raise ValueError('markup-motion-sequence-v1 schema required')
    provenance = document.get('provenance')
    if provenance not in ('authored_synthetic', 'caller_supplied_observation'):
        raise ValueError('explicit provenance required')
    data = deepcopy(document)
    pending = [f32(x) for x in data['pending_before']]
    if len(pending) != 4:
        raise ValueError('four pending lanes required')
    bodies = data['bodies']
    if len(bodies) not in (1, 2):
        raise ValueError('main and optional rider body required')
    events = []
    for index, event in enumerate(data['events']):
        before = list(pending)
        kind = event['kind']
        if kind == 'produce':
            request = dict(event['producer'], schema='markup-vector-bench-v1',
                           provenance=provenance, pending_before=pending)
            result = inspect_producer(request)
            if result['pending_after'] is None:
                return dict(schema='markup-motion-sequence-result-v1', provenance=provenance,
                            status='nonfinite_producer_stopped', stopped_at=index,
                            events=events, failed_producer=result,
                            pending=list(pending), bodies=bodies, boundaries=BOUNDARIES)
            pending = result['pending_after']
        elif kind == 'consume':
            reached = event['consumer_reached']
            if type(reached) is not bool:
                raise ValueError('consumer_reached must be an explicit boolean')
            if reached:
                result = consume_pending_impulse(pending, bodies)
                pending = list(result['pending'])
                for body, submission in zip(bodies, result['submissions']):
                    body['linear'] = list(submission['linear'])
                    body['angular'] = list(submission['angular'])
            else:
                result = dict(consumed=False, skipped=True, submissions=[], lock_scope=False)
        elif kind in ('directional_points', 'summed_points'):
            if type(event['loop_reached']) is not bool:
                raise ValueError('loop_reached must be an explicit boolean')
            submissions = []
            if event['loop_reached']:
                if kind == 'directional_points':
                    submissions = directional_submissions(event['records'], event['combined_scale'])
                else:
                    submissions = summed_submissions(event['records'], event['gate_one'],
                                                     event['gate_other'], event['runtime_scale'])
            effects = []
            for submission in submissions:
                geometry = event['main_geometry']
                world_inertia = world_inverse_inertia(geometry['basis'], geometry['local_inverse_inertia'])
                main = bodies[0]
                effect = apply_point_impulse(main['linear'], main['angular'],
                    submission['impulse'][:3], submission['point'][:3], main['inverse_mass'],
                    geometry['local_center'], geometry['translation'], geometry['basis'], world_inertia,
                    kind=main.get('kind', 0), flags=main.get('flags', 0), force=submission['force'])
                main['linear'] = list(effect['linear'])
                main['angular'] = list(effect['angular'])
                effects.append(dict(record_index=submission['index'], **effect))
            result = dict(skipped=not event['loop_reached'], submissions=submissions, effects=effects)
        else:
            raise ValueError('unknown sequence event')
        events.append(dict(index=index, kind=kind, pending_before=before,
                           pending_after=list(pending), result=result, bodies=deepcopy(bodies)))
    return dict(schema='markup-motion-sequence-result-v1', provenance=provenance,
                status='computed', events=events, pending=list(pending), bodies=bodies,
                boundaries=BOUNDARIES)


BOUNDARIES = [
    'event order and consumer reachability supplied by caller, not recovered live scheduling',
    'body identities, lifetimes, locks and forces outside the supplied events not modeled',
    'point-loop reachability, resolved scales, records and main-body geometry supplied by caller',
    'producer state is post-dispatch state supplied by caller',
    'finite arithmetic only; native dispatch side effects remain external',
    'no integration of position and no game mutation',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(json.loads(args.input.read_text())), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
