import unittest
from reference.snow_charge_release import update_release


class SnowChargeReleaseTests(unittest.TestCase):
    def step(self, state=None, **kwargs):
        state=state or dict(cooked=1,saved_charge=1,elapsed=0,rate=0,release_signal=0,release_copy=0)
        inputs=dict(new_cooked=0,raw_remapped_charge=0,elapsed_dt=.125,derivative_dt=.125,
                    release_threshold=.25,input_update_mode=1)
        inputs.update(kwargs)
        return update_release(state,**inputs)

    def test_quick_release_fires_once_and_clears_saved_charge(self):
        first=self.step(); self.assertEqual(first['release_signal'],1)
        self.assertEqual(first['saved_charge'],0)
        self.assertEqual(self.step(first)['release_signal'],0)

    def test_exact_threshold_rejects_release(self):
        result=self.step(elapsed_dt=.25)
        self.assertEqual(result['release_signal'],0)
        self.assertEqual(result['saved_charge'],0)

    def test_raw_zero_without_cooked_zero_is_not_release(self):
        result=self.step(new_cooked=.5)
        self.assertEqual(result['release_signal'],0)
        self.assertEqual(result['saved_charge'],1)

    def test_rate_minus_one_is_not_slow_decay(self):
        exact=self.step(new_cooked=.5,derivative_dt=.5)
        slow=self.step(new_cooked=.5,derivative_dt=1)
        self.assertEqual(exact['saved_charge'],1)
        self.assertEqual(slow['saved_charge'],0)
        self.assertEqual(slow['elapsed'],0)

    def test_stable_charge_refreshes_elapsed_on_equality(self):
        result=self.step(new_cooked=1,raw_remapped_charge=1)
        self.assertEqual(result['elapsed'],0)
        self.assertEqual(result['rate'],0)

    def test_other_mode_preserves_signals_and_rate(self):
        state=dict(cooked=1,saved_charge=1,elapsed=0,rate=4,release_signal=.5,release_copy=.5)
        result=self.step(state,input_update_mode=2)
        for key in ('saved_charge','rate','release_signal','release_copy'):
            self.assertEqual(result[key],state[key])
        self.assertEqual(result['cooked'],0)
        self.assertEqual(result['elapsed'],.125)

    def test_derivative_clock_changes_rate_not_elapsed(self):
        a=self.step(new_cooked=.75,derivative_dt=.125)
        b=self.step(new_cooked=.75,derivative_dt=.25)
        self.assertEqual((a['rate'],b['rate']),(-2,-1))
        self.assertEqual(a['elapsed'],b['elapsed'])
