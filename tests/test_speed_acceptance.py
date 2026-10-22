from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from speed_acceptance import run_speed_acceptance


class Client:
    def __init__(self,failure=None,resume='completed',held=False):
        self.failure=failure;self.resume=resume;self.held=held;self.calls=[]
    def call(self,method,**params):
        self.calls.append(method)
        if method==self.failure:raise TimeoutError('uncertain '+method)
        if method=='simulation.status':return dict(host_paused=self.held)
        if method=='player.get':return dict(identity='fixture',flags=3,linear_velocity=[10,0,0],angular_velocity=[0,0,0])
        if method=='player.adjust_speed':
            target=10+params['delta_speed'];return dict(speed_target=target,after=dict(linear_velocity=[target,0,0]))
        if method=='simulation.step_world':return dict(requested=params['count'],completed=params['count'],exactly_one=params['count'])
        return {}
    def request(self,method,**params):self.calls.append(method);return dict(status=self.resume)


class SpeedAcceptanceTests(unittest.TestCase):
    def run_trial(self,c):return run_speed_acceptance(c,lambda _:None,lambda:None,sleep=lambda _:None)
    def test_success_requires_both_pulses_and_resume(self):
        c=Client();r=self.run_trial(c);self.assertTrue(r['ok']);self.assertEqual(len(r['trials']),2)
        self.assertEqual(c.calls.count('player.adjust_speed'),2)
    def test_uncertain_pause_and_adjust_are_not_retried(self):
        for method in ('simulation.pause','player.adjust_speed'):
            c=Client(failure=method);r=self.run_trial(c)
            self.assertFalse(r['ok']);self.assertEqual(c.calls.count(method),1)
            self.assertEqual(c.calls[-1],'simulation.resume')
            self.assertIn('uncertain',r['trials'][0]['error'])
    def test_recovery_failure_retains_successful_mutation_evidence(self):
        r=self.run_trial(Client(resume='failed'));self.assertFalse(r['ok'])
        self.assertIn('adjust',r['trials'][0]);self.assertIn('recovery_error',r['trials'][0])
    def test_existing_hold_not_released(self):
        c=Client(held=True);self.assertFalse(self.run_trial(c)['ok'])
        self.assertEqual(c.calls,['simulation.status'])

    def test_consistent_but_wrong_step_counters_fail_without_second_step(self):
        c=Client();original=c.call
        def call(method, **params):
            result=original(method, **params)
            if method=='simulation.step_world':
                return dict(requested=0,completed=0,exactly_one=0)
            return result
        c.call=call
        r=self.run_trial(c)
        self.assertFalse(r['ok'])
        self.assertEqual(c.calls.count('simulation.step_world'),1)
        self.assertEqual(c.calls[-1],'simulation.resume')

    def test_wrong_target_or_malformed_readback_never_steps(self):
        for variant in ('unchanged', 'empty', 'short', 'nan'):
            with self.subTest(variant=variant):
                c=Client();original=c.call
                def call(method, **params):
                    result=original(method, **params)
                    if method=='player.adjust_speed':
                        if variant=='unchanged':
                            result=dict(speed_target=10,after=dict(linear_velocity=[10,0,0]))
                        else:
                            result['after']['linear_velocity']={
                                'empty':[], 'short':[8], 'nan':[float('nan'),0,0]}[variant]
                    return result
                c.call=call
                r=self.run_trial(c)
                self.assertFalse(r['ok'])
                self.assertNotIn('simulation.step_world',c.calls)
                self.assertEqual(c.calls.count('player.adjust_speed'),1)
                self.assertEqual(c.calls[-1],'simulation.resume')
