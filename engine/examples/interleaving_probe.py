"""Explore all bounded symbolic two-worker schedules for a two-receiver job."""
import json
from engine.interleavings import explore


def run():
    return explore([
        dict(id='motion', kind='range', receivers=[0,1], successors=['published']),
        dict(id='published', kind='terminal')],
        dict(shared_default=2, worker_slots=[True,True], jobs={
            'motion':dict(category=1,limit=2)}), ['motion'])


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
