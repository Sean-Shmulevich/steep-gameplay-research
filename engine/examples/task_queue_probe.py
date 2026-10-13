"""Two consumers advancing the queue before the first payload copy."""
import json
from engine.task_queue_probe import TaskQueueProbe


def main():
    probe = TaskQueueProbe(['first-task', 'second-task'])
    for worker, target in [(0, 'copy'), (1, 'return')]:
        for _ in range(100):
            if probe.workers[worker]['phase'] == target:
                break
            probe.step(worker)
        else:
            raise RuntimeError('probe phase bound exceeded')
    probe.step(1)
    for _ in range(100):
        for worker, state in enumerate(probe.workers):
            if state['phase'] != 'done':
                probe.step(worker)
        if probe.snapshot()['complete']:
            break
    snapshot = probe.snapshot()
    print(json.dumps(dict(scope='synthetic prelinked queue; no producers or node reuse',
                          complete=snapshot['complete'], returned=snapshot['returned'],
                          steps=len(snapshot['trace'])), indent=2))
    if not snapshot['complete']:
        raise RuntimeError('probe did not finish')


if __name__ == '__main__':
    main()
