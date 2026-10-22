from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from update_capture_probe import capture_update

class UpdateCaptureControllerTests(unittest.TestCase):
    def fixture(self, root, restored=1, count=1):
        (root/'plugins').mkdir()
        summary={'installed':1,'restored':restored,'drained':1,'records':count,'dropped':0}
        row={'before':{'valid':7,'gates':[1,0,1,1],'request':3},'after':{'valid':7}}
        client=Mock()
        def call(method,**kw):
            if method=='simulation.status':
                return {'host_paused':False,'engine':{'held':False}}
            if method=='simulation.pause':
                (root/'snow_host.log').write_text('capture configured; resume starts bounded observation\n')
            elif method=='simulation.resume':
                (root/'plugins/update_capture.ini.trace.jsonl').write_text('\n'.join(json.dumps(x) for x in [summary]+[row]*count)+'\n')
            return {'ok':True}
        client.call.side_effect=call
        return client
    def test_complete_capture(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); client=self.fixture(root)
            result=capture_update(client,root)
            self.assertTrue(result['ok']); self.assertEqual(result['valid_pairs'],1)
            self.assertEqual(result['request_count'],1)
            self.assertEqual(client.call.call_args_list[-1].args,('simulation.resume',))
    def test_required_attribution_missing_is_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); client=self.fixture(root)
            (root/'plugins/update_capture.ini').write_text('[capture]\nattribute_jobs=1\n')
            result=capture_update(client,root)
            self.assertFalse(result['ok'])
            self.assertTrue(result['attribution_required'])
            self.assertEqual(result['attributed_records'],0)

    def test_restoration_failure_is_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.assertFalse(capture_update(self.fixture(root,restored=0),root)['ok'])
    def test_empty_capture_is_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.assertFalse(capture_update(self.fixture(root,count=0),root)['ok'])
    def test_timeout_still_resumes(self):
        with tempfile.TemporaryDirectory() as d:
            client=Mock()
            client.call.return_value={'host_paused':False}
            with self.assertRaisesRegex(RuntimeError,'configuration'):
                capture_update(client,Path(d),timeout=0)
            self.assertEqual(client.call.call_args_list[-1].args,('simulation.resume',))
    def test_stale_export_refused_before_pause(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'plugins').mkdir(); (root/'plugins/update_capture.ini.trace.jsonl').write_text('{}')
            client=Mock()
            with self.assertRaisesRegex(RuntimeError,'pre-existing'): capture_update(client,root)
            client.call.assert_not_called()

    def test_existing_pause_is_not_taken_over(self):
        for status in ({'host_paused':True}, {'host_paused':False,'engine':{'held':True}}):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as d:
                client=Mock(); client.call.return_value=status
                with self.assertRaisesRegex(RuntimeError,'Already held'):
                    capture_update(client,Path(d))
                client.call.assert_called_once_with('simulation.status')

    def test_confirmed_resume_is_not_repeated(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); client=self.fixture(root)
            result=capture_update(client,root)
            self.assertTrue(result['ok'])
            self.assertEqual(sum(c.args==('simulation.resume',) for c in client.call.call_args_list),1)

    def test_resume_failure_does_not_hide_configuration_failure(self):
        with tempfile.TemporaryDirectory() as d:
            client=Mock()
            def call(method,**kw):
                if method=='simulation.resume': raise RuntimeError('transport lost')
                return {'host_paused':False}
            client.call.side_effect=call
            with self.assertRaisesRegex(RuntimeError,'configuration'):
                capture_update(client,Path(d),timeout=0)
            self.assertEqual(client.call.call_args_list[-1].args,('simulation.resume',))
