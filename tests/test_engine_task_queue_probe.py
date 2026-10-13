import unittest
from engine.task_queue_probe import TaskQueueProbe


def until(probe, worker, phase):
    for _ in range(100):
        if probe.workers[worker]['phase'] == phase:
            return
        probe.step(worker)
    raise AssertionError('phase was not reached')


def drain(probe):
    for _ in range(1000):
        for i, worker in enumerate(probe.workers):
            if worker['phase'] != 'done':
                probe.step(i)
        if probe.snapshot()['complete']:
            return
    raise AssertionError('probe failed to drain')


class TaskQueueProbeTests(unittest.TestCase):
    def test_competing_head_cas_returns_each_task_once(self):
        p = TaskQueueProbe(['a', 'b'])
        until(p, 0, 'cas_head')
        until(p, 1, 'cas_head')
        self.assertTrue(p.step(0)['success'])
        self.assertFalse(p.step(1)['success'])
        drain(p)
        self.assertCountEqual([r['payload'] for r in p.returned], ['a', 'b'])
        self.assertCountEqual([r['node'] for r in p.returned], [1, 2])

    def test_head_can_advance_twice_before_first_payload_copy(self):
        p = TaskQueueProbe(['a', 'b'])
        until(p, 0, 'copy')
        until(p, 1, 'return')
        p.step(1)
        self.assertEqual([r['payload'] for r in p.returned], ['b'])
        drain(p)
        self.assertEqual([r['payload'] for r in p.returned], ['b', 'a'])
        self.assertEqual(p.head & ((1 << 48) - 1), 3)

    def test_stale_observation_retries_without_retiring_node(self):
        p = TaskQueueProbe(['a'])
        until(p, 1, 'recheck')
        until(p, 0, 'copy')
        self.assertEqual(p.step(1).get('retry'), 'head_changed')
        self.assertEqual(p.returned, [])
        drain(p)
        self.assertEqual(len(p.returned), 1)

    def test_lagging_tail_is_helped_before_dequeue(self):
        p = TaskQueueProbe(['a', 'b'], tail_index=0)
        drain(p)
        self.assertTrue(any(e['action'] == 'cas_tail' and e['success'] for e in p.trace))
        self.assertCountEqual([r['payload'] for r in p.returned], ['a', 'b'])

    def test_empty_and_snapshot_isolation(self):
        p = TaskQueueProbe([])
        state = p.snapshot()
        state['nodes'][1]['next'] = 99
        drain(p)
        self.assertEqual(p.returned, [])
        with self.assertRaises(ValueError):
            p.step(0)
