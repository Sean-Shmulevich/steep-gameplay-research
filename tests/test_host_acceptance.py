import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
import host_acceptance


class AcceptanceTests(unittest.TestCase):
    def client(self):
        c=Mock();c.call.return_value=dict(identity='synthetic',flags=3);return c

    def test_all_stages_required_and_ordered(self):
        c=self.client();speed=Mock(return_value={'ok':True})
        with patch.object(host_acceptance,'demo',return_value={'ok':True}) as demo:
            report=host_acceptance.run_acceptance(c,speed,steps=3)
        self.assertTrue(report['ok'])
        self.assertEqual([s['name'] for s in report['stages']],['player','pause_step_resume','brake_boost','player_after'])
        demo.assert_called_once_with(c,3,30000);speed.assert_called_once_with()

    def test_no_mutations_without_simulated_player(self):
        c=self.client();c.call.return_value=dict(identity='synthetic',flags=1);speed=Mock()
        with patch.object(host_acceptance,'demo') as demo:
            report=host_acceptance.run_acceptance(c,speed)
        self.assertFalse(report['ok']);demo.assert_not_called();speed.assert_not_called()

    def test_step_failure_stops_speed_trial_and_preserves_recovery(self):
        speed=Mock();failure=dict(ok=False,resume_error='uncertain')
        with patch.object(host_acceptance,'demo',return_value=failure):
            report=host_acceptance.run_acceptance(self.client(),speed)
        self.assertFalse(report['ok']);speed.assert_not_called()
        self.assertEqual(report['stages'][-1]['result'],failure)

    def test_speed_failure_is_not_partial_success(self):
        with patch.object(host_acceptance,'demo',return_value={'ok':True}):
            report=host_acceptance.run_acceptance(self.client(),Mock(side_effect=TimeoutError('lost response')))
        self.assertFalse(report['ok']);self.assertEqual(len(report['stages']),3)
        self.assertIn('lost response',report['stages'][-1]['error'])

    def test_read_only_wait_for_world_membership(self):
        c=self.client()
        c.call.side_effect=[dict(identity=1,flags=1),dict(identity=1,flags=3),dict(identity=1,flags=3)]
        with patch.object(host_acceptance.time,'sleep'), patch.object(host_acceptance,'demo',return_value={'ok':True}):
            report=host_acceptance.run_acceptance(c,lambda:{'ok':True},ready_wait_seconds=1)
        self.assertTrue(report['ok'])
        self.assertEqual([r['flags'] for r in report['readiness_samples']],[1,3])
        self.assertTrue(all(call.args==('player.get',) for call in c.call.call_args_list))

    def test_readiness_transport_failure_not_retried(self):
        c=self.client();c.call.side_effect=TimeoutError('read timeout')
        with patch.object(host_acceptance,'demo') as demo:
            report=host_acceptance.run_acceptance(c,Mock(),ready_wait_seconds=20)
        self.assertFalse(report['ok']);self.assertEqual(c.call.call_count,1)
        demo.assert_not_called()

    def test_preparation_uses_input_only_for_inactive_player(self):
        c=Mock();c.call.side_effect=[{'ordinary':True}, {'identity':1,'flags':1}, {'identity':1,'flags':3}]
        pulse=Mock(return_value={'exit_code':0,'keys_released':True})
        r=host_acceptance.prepare_rider(c,pulse)
        self.assertTrue(r['ok']);pulse.assert_called_once_with()
        self.assertEqual([x.args[0] for x in c.call.call_args_list],['simulation.status','player.get','player.get'])
        self.assertFalse(r['game_input_ingestion_verified'])

    def test_preparation_refuses_paused_and_uncertain_release(self):
        c=Mock();c.call.return_value={'ordinary':True,'host_paused':True};pulse=Mock()
        self.assertFalse(host_acceptance.prepare_rider(c,pulse)['ok']);pulse.assert_not_called()
        c.call.side_effect=[{'ordinary':True},{'identity':1,'flags':1}]
        pulse.return_value={'exit_code':0,'keys_released':False}
        self.assertFalse(host_acceptance.prepare_rider(c,pulse)['ok'])
        pulse.assert_called_once_with()

    def test_active_player_needs_no_input(self):
        c=Mock();c.call.side_effect=[{'ordinary':True},{'identity':1,'flags':3}];pulse=Mock()
        self.assertTrue(host_acceptance.prepare_rider(c,pulse)['ok']);pulse.assert_not_called()
