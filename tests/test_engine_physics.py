import copy
import math
import unittest
from engine.physics import step


class Plane:
    def __init__(self, slope=0, grip=1):
        self.slope, self.grip = slope, grip

    def sample(self, x, y):
        return dict(height=self.slope*x, normal=[-self.slope, 0, 1], velocity=[0,0,0],
                    material=dict(name='synthetic', density=300, thickness=.1,
                                  normal_frequency=2, tangent_frequency=.1, grip=self.grip))


def rider():
    return dict(position=[0,0,0], velocity=[0,0,0], orientation=[0,0,0,1],
                angular_velocity=[0,0,0], mass=70., grounded=True)


class PhysicsTests(unittest.TestCase):
    def test_rest_and_brake_do_not_spin(self):
        b = rider()
        for _ in range(120):
            step(b, {'brake':True}, Plane(), 1/60, {})
        self.assertEqual(b['position'], [0,0,0])
        self.assertEqual(b['orientation'], [0,0,0,1])

    def test_slope_gravity_and_surface_constraint(self):
        b = rider()
        world = Plane(-.25)
        for _ in range(120):
            step(b, {}, world, 1/60, {})
        self.assertGreater(b['velocity'][0], 1)
        self.assertGreaterEqual(b['position'][2] + 1e-8, -.25*b['position'][0])

    def test_brake_stops_without_reversing(self):
        b = rider()
        b['velocity'] = [5,0,0]
        for _ in range(120):
            step(b, {'brake':True}, Plane(), 1/60, {})
            self.assertGreaterEqual(b['velocity'][0], 0)
        self.assertLess(b['velocity'][0], .001)

    def test_grip_reduces_side_slip(self):
        loose, grippy = rider(), rider()
        loose['velocity'] = grippy['velocity'] = [3,3,0]
        step(loose, {}, Plane(grip=0), 1/60, {})
        step(grippy, {}, Plane(grip=2), 1/60, {})
        self.assertLess(grippy['velocity'][1], loose['velocity'][1])

    def test_jump_release_and_landing_event(self):
        b = rider()
        for _ in range(30):
            d = step(b, {'jump':True}, Plane(), 1/60, {})
            self.assertFalse(d['events'])
        d = step(b, {}, Plane(), 1/60, {})
        self.assertEqual(d['events'][0]['type'], 'jump')
        self.assertFalse(b['grounded'])
        events = []
        for _ in range(180):
            events.extend(step(b, {}, Plane(), 1/60, {})['events'])
        self.assertEqual(len([e for e in events if e['type']=='landing']), 1)
        self.assertTrue(b['grounded'])

    def test_air_rotation_independent_of_translation_and_persists(self):
        a, b = rider(), rider()
        for item in (a,b):
            item.update(position=[0,0,20], grounded=False)
        for _ in range(20):
            step(a, {'steer':1,'flip':.5}, Plane(), 1/60, {})
            step(b, {}, Plane(), 1/60, {})
        self.assertEqual(a['position'], b['position'])
        self.assertEqual(a['velocity'], b['velocity'])
        omega = a['angular_velocity'][:]
        step(a, {}, Plane(), 1/60, {})
        self.assertEqual(a['angular_velocity'], omega)
        self.assertAlmostEqual(sum(v*v for v in a['orientation']), 1)

    def test_walking_uses_independent_intent_servo(self):
        b = rider()
        for _ in range(120):
            step(b, {'tuck':True}, Plane(), 1/60, {'sport':'walking'})
        self.assertAlmostEqual(b['velocity'][0], 2.5, places=5)
        for _ in range(120):
            step(b, {}, Plane(), 1/60, {'sport':'walking'})
        self.assertLess(b['velocity'][0], .001)

    def test_checkpoint_determinism(self):
        a = rider()
        for _ in range(10):
            step(a, {'jump':True,'steer':.4}, Plane(), 1/60, {})
        b = copy.deepcopy(a)
        for _ in range(40):
            da = step(a, {'flip':.3}, Plane(), 1/60, {})
            db = step(b, {'flip':.3}, Plane(), 1/60, {})
            self.assertEqual(a,b)
            self.assertEqual(da,db)

    def test_invalid_input_does_not_mutate_body(self):
        for control, dt, config in [({'steer':float('nan')}, .01, {}),
                                    ({}, .5, {}), ({}, .01, {'physics':{'spring_mass':0}})]:
            b = rider()
            original = copy.deepcopy(b)
            with self.assertRaises(ValueError):
                step(b, control, Plane(), dt, config)
            self.assertEqual(b, original)

    def test_inverted_landing_is_classified_explicitly(self):
        b = rider()
        b.update(position=[0,0,.001], velocity=[0,0,-1], grounded=False,
                 orientation=[1,0,0,0])
        d = step(b, {}, Plane(), 1/60, {})
        self.assertEqual(d['events'][0]['quality'], 'crash')
        self.assertEqual(d['events'][0]['policy'], 'synthetic')


if __name__ == '__main__':
    unittest.main()


class ReconstructedSteeringTests(unittest.TestCase):
    def test_runtime_retains_exact_cooker_state_across_reversal(self):
        from reference.input_cooker import cook
        from reference.decay_exp import cooker_table
        from reference.runtime_curve import evaluate
        table=cooker_table(vector_path='sse2',scalar_path='sse2')
        coefficients=dict(baseDampFactorToZero=0.,proportionalDampFactorToZero=12.,
                          baseDampFactorToOne=0.,proportionalDampFactorToOne=9.)
        body=rider(); value=0.
        for target in [1]*20+[-1]*20+[0]*120:
            expected=cook(value,target,1/60,coefficients,
                          decay_lookup=lambda x:evaluate(x,**table))
            result=step(body,{'steer':target},Plane(),1/60,{})
            self.assertEqual(result['steering_cooker'],expected)
            self.assertEqual(body['_snow_physics']['steer'],expected['value'])
            self.assertIn('synthetic coefficients',result['evidence']['steering_filter'])
            value=expected['value']
        self.assertEqual(value,0)
