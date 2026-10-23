import unittest
from engine.root_stop import request_root_stop
from engine.frame_submission import finish_root_cycle, wait_root_event


class RootStopTests(unittest.TestCase):
    def test_late_owner_and_two_distinct_receiver_reads(self):
        events = []; receivers = iter(['first', 'second'])
        owner = dict(byte_46=0)
        def lookup():
            value = next(receivers); events.append(('lookup', value)); return value
        def invoke(receiver):
            events.append(('invoke', receiver))
        request_root_stop(configure_service=lambda *a: events.append(('configure', a)),
            followup_service=lambda: events.append(('followup',)), get_optional_receiver=lookup,
            invoke_receiver=invoke, read_owner=lambda: events.append(('owner',)) or owner,
            set_global_requested=lambda value: events.append(('global', value, owner['byte_46'])))
        self.assertEqual(events, [('configure', (64, 15, True)), ('followup',),
            ('lookup', 'first'), ('lookup', 'second'), ('invoke', 'second'),
            ('owner',), ('global', 1, 0)])
        self.assertEqual(owner['byte_46'], 1)

    def test_missing_owner_still_sets_global(self):
        flags = []
        request_root_stop(configure_service=lambda *a: None, followup_service=lambda: None,
            get_optional_receiver=lambda: None, invoke_receiver=lambda r: self.fail('invoked'),
            read_owner=lambda: None, set_global_requested=flags.append)
        self.assertEqual(flags, [1])

    def test_stop_then_callback_then_wait_is_not_immediate_signal(self):
        owner = dict(byte_0=1, byte_46=0, root_job='root', event='event')
        state = dict(requested=0, signaled=False)
        request_root_stop(configure_service=lambda *a: None, followup_service=lambda: None,
            get_optional_receiver=lambda: None, invoke_receiver=lambda r: None,
            read_owner=lambda: owner,
            set_global_requested=lambda v: state.update(requested=v))
        self.assertFalse(state['signaled'])
        self.assertEqual(owner['byte_0'], 1)
        def signal(event):
            state['signaled'] = True
            return 1
        finish_root_cycle(owner, barrier=lambda: None, current_context=lambda: None,
            service_context=lambda c: None, finish_service=lambda: None,
            service_global=lambda: None, prepare_next_cycle=lambda o: None,
            submit_job=lambda j: self.fail('stop resubmitted'), signal_event=signal)
        def wait(event, timeout):
            self.assertTrue(state['signaled'])
            return 0
        wait_root_event(read_owner=lambda: owner, wait=wait)
        self.assertEqual(owner['byte_0'], 0)
        self.assertEqual(state['requested'], 1)
