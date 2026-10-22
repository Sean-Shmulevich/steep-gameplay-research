import unittest
import json
from engine.control import SchedulerController
from engine.replay import replay
from reference.central_impulse import central_impulse

class EngineImpulseTests(unittest.TestCase):
    def test_mass_scaled_float32_result_and_replay(self):
        c=SchedulerController({'body':{'mass':20,'velocity':[3,4,0],'angular_velocity':[1.123456789,2,3]}})
        old=c.pause();before=c.snapshot()['state']
        token=c.apply_central_impulse(old,[40,0,0]);after=c.snapshot()['state']
        expected=central_impulse(before['body']['velocity'],before['body']['angular_velocity'],[40,0,0],.05)
        self.assertEqual(after['body']['velocity'],list(expected['linear']))
        self.assertEqual(after['body']['angular_velocity'],before['body']['angular_velocity'])
        for key in ['tick','time','animation','pose','scheduler']:
            self.assertEqual(before[key],after[key])
        with self.assertRaises(ValueError):c.step_once(old)
        c.step_once(token)
        recording=json.loads(json.dumps(c.export_replay()))
        rebuilt=replay(recording)
        self.assertEqual(rebuilt.snapshot(),c.snapshot()['state'])
        self.assertEqual(rebuilt.events,c.checkpoint()['engine']['events'])

    def test_invalid_or_overflowing_impulse_is_atomic(self):
        c=SchedulerController();token=c.pause();before=c.checkpoint()
        for impulse in ([True,0,0],[float('inf'),0,0],[1e100,0,0],[1,2],None):
            with self.subTest(impulse=impulse),self.assertRaises(ValueError):
                c.apply_central_impulse(token,impulse)
            self.assertEqual(c.checkpoint(),before)
        c.resume(token)
        with self.assertRaises(ValueError):c.apply_central_impulse(token,[1,0,0])

    def test_rigid_angular_momentum_survives(self):
        c=SchedulerController({'physics_mode':'rigid_cells','body':{'angular_velocity':[1,2,3]}})
        token=c.pause();c.step_once(token);before=c.snapshot()['state']
        c.apply_central_impulse(token,[0,0,4]);after=c.snapshot()['state']
        self.assertEqual(after['body']['angular_velocity'],before['body']['angular_velocity'])
        self.assertEqual(after['body']['_rigid']['angular_momentum'],before['body']['_rigid']['angular_momentum'])
