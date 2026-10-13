"""Synthetic two-worker interleaving; no OS threads or game access."""
import json
from engine.mixed_scheduler import MixedScheduler
from engine.queue_producers import range_configuration


def run():
    model = MixedScheduler([
        dict(id='receivers', kind='range', receivers=list(range(100)),
             successors=['finished'], **range_configuration(32)),
        dict(id='finished', kind='terminal')],
        queue_policy=dict(shared_default=2, worker_slots=[True, True],
                          jobs={'receivers':dict(category=1, limit=2)}))
    model.submit('receivers')
    tokens = [model.reserve(worker_index=i) for i in range(2)]
    held = model.claim_range(tokens[0])
    claims = [(0, held.start, held.count)]
    while (claim := model.claim_range(tokens[1])) is not None:
        claims.append((1, claim.start, claim.count))
        model.execute_range(tokens[1], claim)
    model.finish_dispatch(tokens[1])
    blocked = model.snapshot()['jobs']['finished']['terminal_begins'] == 0
    model.execute_range(tokens[0], held)
    model.finish_dispatch(tokens[0])
    snapshot = model.snapshot()
    assert blocked and snapshot['jobs']['finished']['terminal_begins'] == 1
    assert sum(c[2] for c in claims) == 100
    assert snapshot['trace']['dropped'] == 0
    return dict(scope='synthetic serial worker interleaving', claims=claims,
                successor_waited_for_held_range=blocked, snapshot=snapshot)


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
