import unittest
from engine.frame_submission import submit_root_sequence


class RootSubmissionTests(unittest.TestCase):
    def test_order_reload_event_and_late_gate(self):
        old = dict(byte_0=0, byte_46=1, byte_58=1, event='old', root_job='old-root')
        current = [old]; events = []
        new = dict(byte_0=9, byte_46=7, byte_58=1, event='event', root_job='root')
        def prepare():
            events.append('prepare'); current[0] = new
        def reset(event):
            self.assertEqual((new['byte_0'], new['byte_46']), (1, 0))
            self.assertEqual(event, 'event')
            events.append('reset'); new['byte_58'] = 0
            return False  # API failure is not tested by the recovered wrapper.
        def graph(owner):
            self.assertIs(owner, new); events.append('graph')
        def submit(job):
            self.assertEqual(job, 'root'); events.append('submit'); return 17
        result = submit_root_sequence(prepare_service=prepare, read_owner=lambda: current[0],
                                     reset_event=reset, prepare_graph=graph, submit_job=submit)
        self.assertEqual(events, ['prepare', 'reset', 'graph', 'submit'])
        self.assertEqual(result, 17)
        self.assertEqual(old['byte_46'], 1)

    def test_nonzero_gate_skips_graph_but_submits(self):
        for byte in (1, 2, 255):
            owner = dict(byte_58=byte, event='event', root_job='root')
            result = submit_root_sequence(prepare_service=lambda: None, read_owner=lambda: owner,
                reset_event=lambda event: True,
                prepare_graph=lambda owner: self.fail('nonzero gate ran graph setup'),
                submit_job=lambda job: False)
            self.assertIs(result, False)

    def test_reset_exception_leaves_prefix_without_submission(self):
        owner = dict(byte_58=0, event='event', root_job='root')
        def fail(event):
            raise RuntimeError('supplied event service failed')
        with self.assertRaises(RuntimeError):
            submit_root_sequence(prepare_service=lambda: None, read_owner=lambda: owner,
                reset_event=fail, prepare_graph=lambda owner: self.fail('graph ran'),
                submit_job=lambda job: self.fail('submission ran'))
        self.assertEqual((owner['byte_0'], owner['byte_46']), (1, 0))
