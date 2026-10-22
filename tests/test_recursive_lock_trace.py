import json
from pathlib import Path
import unittest
from engine.recursive_lock_trace import inspect_completed_lock_events


class RecursiveLockTraceTests(unittest.TestCase):
    def test_original_adapter_chain(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/registry_lock_chain_validation.json').read_text())
        for sample in receipt['samples']:
            result=inspect_completed_lock_events(sample['lock_trace'])
            self.assertTrue(result['balanced'])
            self.assertEqual(result['max_depth'],sample['max_lock_depth'])
            self.assertFalse(result['trace_completeness_proven'])

    def test_recursion_then_thread_handoff(self):
        events=[dict(operation=op,thread=thread) for op,thread in
                [('enter','a'),('enter','a'),('leave','a'),('leave','a'),('enter','b')]]
        result=inspect_completed_lock_events(events)
        self.assertEqual((result['owner'],result['depth'],result['max_depth']),('b',1,2))
        self.assertFalse(result['balanced'])

    def test_inconsistent_ownership_and_depth_rejected(self):
        for events in ([dict(operation='leave',thread='a')],
                       [dict(operation='enter',thread='a'),dict(operation='enter',thread='b')],
                       [dict(operation='enter',thread='a',depth_after=2)]):
            with self.assertRaises(ValueError):inspect_completed_lock_events(events)
