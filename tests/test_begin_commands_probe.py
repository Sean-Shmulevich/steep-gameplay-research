import unittest
from engine.examples.begin_commands_probe import run_probe


class BeginCommandsProbeTests(unittest.TestCase):
    def test_commands_execute_before_either_mode_branch(self):
        for paused in (False,True):
            with self.subTest(paused=paused):
                result=run_probe(paused)
                self.assertEqual(result['events'],['commands','paused_route' if paused else 'normal_route'])
                self.assertEqual(result['commands'][0]['reattach_targets'],['synthetic-child'])
                self.assertEqual(result['commands'][0]['entity_bytes']['synthetic-child'],128)
                self.assertTrue(result['completed'])

    def test_body_return_does_not_release_dependency_before_dispatch_finish(self):
        result=run_probe(True)
        observation=result['before_dispatch_finish']
        self.assertEqual(observation['commands_executed'],1)
        self.assertEqual(observation['begin_executions'],1)
        self.assertEqual(observation['branch_holds'],1)
        self.assertEqual(observation['branch_requested'],1)  # Requested, but still held.
