import unittest
from engine.animation_update_policy import plan_animation_update


class AnimationUpdatePolicyTests(unittest.TestCase):
    def plan(self, **changes):
        args = dict(pending_count_word=1, graph_state_word=0, mode_flags=1,
                    counter=0, threshold=3, accumulated=0.0, interval=0.125)
        args.update(changes)
        return plan_animation_update(**args)

    def test_accumulation_then_full_update(self):
        first = self.plan()
        self.assertEqual(first, dict(deferred=True, counter=1, accumulated=.125,
                                    branch_interval=.125, reset_parameter_groups=False))
        second = self.plan(counter=first['counter'], accumulated=first['accumulated'])
        third = self.plan(counter=second['counter'], accumulated=second['accumulated'])
        self.assertEqual(third, dict(deferred=False, counter=0, accumulated=0.0,
                                    branch_interval=.375, reset_parameter_groups=True))

    def test_each_gate_and_mask(self):
        for changes in (dict(pending_count_word=0xe0000000), dict(graph_state_word=1),
                        dict(mode_flags=0), dict(mode_flags=5), dict(threshold=0)):
            self.assertFalse(self.plan(**changes)['deferred'])
        self.assertTrue(self.plan(mode_flags=0xfb)['deferred'])
        self.assertTrue(self.plan(pending_count_word=0xe0000001)['deferred'])

    def test_counter_wrap_and_float32_order(self):
        result = self.plan(counter=255, threshold=1)
        self.assertTrue(result['deferred'])
        self.assertEqual(result['counter'], 0)
        self.assertEqual(self.plan(threshold=0, accumulated=16777216, interval=1)['branch_interval'], 16777216)
        self.assertEqual(self.plan(threshold=0, accumulated=.125, interval=-.25)['branch_interval'], -.125)

    def test_invalid_inputs(self):
        for changes in (dict(counter=256), dict(threshold=True), dict(interval=float('inf')),
                        dict(accumulated=1e100), dict(graph_state_word=-1)):
            with self.assertRaises(ValueError):
                self.plan(**changes)
