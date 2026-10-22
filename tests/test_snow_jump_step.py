import unittest
from reference.snow_jump_step import jump_step
from reference.central_impulse import f32


class SnowJumpStepTests(unittest.TestCase):
    def run_step(self, **changes):
        values=dict(cached_factor=7,cooldown=0,elapsed_dt=.01,air_time=0,base_factor=80,
                    release_signal=1,coil_gain=.75,depth_gain=.5,speed_gain=1.25,gravity=10,
                    combined_mass=80,configured_rider_mass=20,rider_present=True)
        values.update(changes)
        return jump_step(**values)

    def test_order_mass_split_and_reset(self):
        result=self.run_step()
        self.assertEqual(result['cached_factor'],3.75)
        self.assertEqual([x['body'] for x in result['submissions']],['rider','main'])
        self.assertEqual([x['impulse'][2] for x in result['submissions']],[75,225])
        self.assertEqual(result['cooldown'],f32(.333))

    def test_disabled_clears_both_even_with_release(self):
        for changes in ({'air_time':.01},{'base_factor':0}):
            result=self.run_step(cooldown=1,**changes)
            self.assertEqual((result['cached_factor'],result['cooldown'],result['submissions']),(0,0,()))

    def test_positive_cooldown_retains_factor(self):
        result=self.run_step(cooldown=.02)
        self.assertEqual(result['branch'],'cooldown')
        self.assertEqual(result['cached_factor'],7)

    def test_exact_expiry_allows_release_and_no_release_clears_factor(self):
        self.assertEqual(self.run_step(cooldown=.01)['branch'],'submit')
        result=self.run_step(release_signal=0)
        self.assertEqual(result['branch'],'no_release')
        self.assertLess(result['cooldown'],0)
        self.assertEqual(result['cached_factor'],0)

    def test_zero_gain_still_submits_and_resets(self):
        result=self.run_step(coil_gain=0)
        self.assertEqual(len(result['submissions']),2)
        self.assertTrue(all(x['impulse']==(0,0,0) for x in result['submissions']))
        self.assertEqual(result['cooldown'],f32(.333))

    def test_absent_rider_keeps_unclamped_main_split(self):
        result=self.run_step(rider_present=False,combined_mass=10)
        self.assertEqual(len(result['submissions']),1)
        self.assertEqual(result['submissions'][0]['impulse'],(0,0,-37.5))

    def test_airtime_does_not_buffer_release(self):
        first=self.run_step(air_time=1)
        second=self.run_step(cached_factor=first['cached_factor'],cooldown=first['cooldown'],release_signal=0)
        self.assertEqual(second['submissions'],())
