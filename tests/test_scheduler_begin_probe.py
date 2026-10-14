import unittest
from engine.examples.scheduler_begin_probe import run_probe


class SchedulerBeginProbeTests(unittest.TestCase):
    def test_empty_ranges_finish_without_reservations(self):
        result = run_probe()
        final = result['boundary_observations'][-1]
        self.assertEqual(final['queue'], [])
        for job in final['jobs'].values():
            self.assertEqual(job['requested'], 1)
            self.assertEqual(job['started'], 1)
            self.assertEqual(job['executions'], 0)
            self.assertEqual(job['outstanding_dispatches'], 0)
        empty = [e['job'] for e in result['trace']['records'] if e['kind'] == 'mixed_empty_begin_done']
        self.assertEqual(set(empty), {'UpdateCharacterActionSet', 'SkelUpdateBeginAnimate',
                                    'AnimationUpdateTime', 'UpdateActionKinoStatesInteraction'})

    def test_boundary_zero_counts_do_not_erase_callback_execution(self):
        result = run_probe()
        for boundary in result['boundary_observations']:
            self.assertTrue(all(j['executions'] == 0 for j in boundary['jobs'].values()))
        self.assertEqual([o['job'] for o in result['callback_observations']],
                         ['UpdatePreActionGather', 'UpdateKino', 'ActionGatherComponents'])
        for inside in result['callback_observations']:
            self.assertEqual(inside['executions'], 1)
            self.assertEqual(inside['outstanding_dispatches'], 1)
