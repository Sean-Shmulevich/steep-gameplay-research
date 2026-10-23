"""Public combined native-code probe; does not launch or inspect a game."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CommandPipelineProbeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'), 'native C compiler unavailable')
    def test_admission_is_distinct_from_delivery_and_unload(self):
        run = subprocess.run([sys.executable, str(ROOT/'scripts/run_command_pipeline_probe.py')],
                             check=True, capture_output=True, text=True, timeout=80)
        report = json.loads(run.stdout)
        self.assertFalse(report['game_launched'])
        self.assertFalse(report['native_phase_proved'])
        self.assertFalse(report['native_lifetime_proved'])
        self.assertFalse(report['unload_safety_proved'])
        requests = {r['id']: r for r in report['requests']}
        self.assertEqual(requests[101], dict(id=101, admission='submitted',
                                          observed_deliveries=2, recorder_dropped=1,
                                          ownership_finalized=1, synthetic_invocations=4, ownership_release_path="queue_cleanup"))
        self.assertEqual(requests[102]['admission'], 'submitted')
        self.assertEqual(requests[102]['observed_deliveries'], 0)
        self.assertEqual(requests[102]['synthetic_invocations'], 0)
        self.assertEqual(requests[103]['admission'], 'full')
        self.assertEqual(requests[104]['admission'], 'stale_binding')
        self.assertTrue(all(r['ownership_finalized'] == 1 for r in requests.values()))
        self.assertEqual(requests[102]['ownership_release_path'], 'queue_cleanup')
        for i in (103,104):
            self.assertEqual(requests[i]['ownership_release_path'], 'caller_after_refusal')
            self.assertEqual(requests[i]['observed_deliveries'], 0)
        self.assertEqual(report['queue_remaining'], 0)
        self.assertEqual(report['synthetic_disposals_without_invocation'], 1)
        self.assertTrue(report['cached_call_after_close_returned'])

        correlation = report['phase_correlation']
        self.assertEqual(correlation['command_records'], 2)
        self.assertEqual(correlation['phase_records'], 4)
        self.assertEqual([m['phase_indexes'] for m in correlation['matches']], [[0], [1]])
        self.assertEqual({r['thread'] for r in report['command_records']}, {1, 2})
        self.assertEqual(correlation['command_dropped'], 1)
        self.assertFalse(correlation['native_phase_proved'])
