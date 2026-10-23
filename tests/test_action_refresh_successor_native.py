"""Compare independent release/begin to synthetic original-instruction outcomes.

Fixture seeding uses private model state to select the exact release boundary.
This does not test model activation, reservation or native concurrent dispatch.
"""
import json
from pathlib import Path
import unittest
from engine.mixed_scheduler import MixedScheduler


class NativeSuccessorComparisonTests(unittest.TestCase):
    def test_release_and_begin_match_native_fixtures(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/action_refresh_successor.json').read_text())
        self.assertEqual(len(fixture['cases']), 24)
        for case in fixture['cases']:
            initial = case['initial']
            with self.subTest(initial=initial):
                model = MixedScheduler([
                    dict(id='predecessor', kind='callback', successors=['successor']),
                    dict(id='successor', kind='range',
                         receivers=list(range(initial['remaining'])),
                         credit_gate=initial['credit_gate'], credits=initial['credits'])])
                job = model._jobs['successor']
                job.update({key: initial[key] for key in ('holds', 'started', 'requested')})
                model._lists['predecessor']['primary']['active'] = True
                model._normal_release('predecessor', 'primary', None)
                actual = model.snapshot()['jobs']['successor']
                self.assertEqual({key: actual[key] for key in case['expected']}, case['expected'])
                self.assertEqual('successor' in model.snapshot()['queue'],
                                 case['expected']['state'] == 'SCHEDULED')
                self.assertFalse(model.snapshot()['lists']['predecessor']['primary']['active'])


if __name__ == '__main__':
    unittest.main()
