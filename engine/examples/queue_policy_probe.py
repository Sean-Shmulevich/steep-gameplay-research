"""Synthetic queue routing example; assignments are supplied, not game defaults."""
import json
from engine.mixed_scheduler import MixedScheduler


def run_probe():
    names = ['later_local', 'shared_blocked', 'shared_allowed', 'first_local']
    definitions = [dict(id=name, kind='callback') for name in names]
    policy = dict(shared_default=8, worker_mask=1, jobs={
        'later_local': dict(category=1, queue='local', limit=1),
        'shared_blocked': dict(category=0, queue='shared', limit=1, required_mask=2),
        'shared_allowed': dict(category=0, queue='shared', limit=1, required_mask=1),
        'first_local': dict(category=0, queue='local', limit=1, excluded_mask=1),
    })
    model = MixedScheduler(definitions, queue_policy=policy)
    for name in names:
        model.submit(name)
    observed = []
    for _ in range(3):
        before = model.snapshot()
        model.ready()
        assert model.snapshot() == before
        token = model.reserve()
        assert token is not None
        after = model.snapshot()
        name = after['dispatches'][str(token.dispatch)]['job']
        observed.append(name)
        model.execute_callback(token)
        model.finish_dispatch(token)
    assert observed == ['first_local', 'shared_allowed', 'later_local'], observed
    assert model.reserve() is None
    final = model.snapshot()
    assert final['jobs']['shared_blocked']['state'] == 'SCHEDULED'
    return dict(scope='Synthetic assignments exercising recovered queue selection',
                selected=observed, affinity_blocked='shared_blocked',
                blocked_job_remains_scheduled=True, trace=final['trace'])


if __name__ == '__main__':
    print(json.dumps(run_probe(), indent=2))
