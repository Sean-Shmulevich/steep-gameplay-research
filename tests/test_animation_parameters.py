import unittest
from engine.animation_parameters import ParameterGroup, prepare_parameter, reset_parameter_groups


class ParameterPreparationTests(unittest.TestCase):
    def test_shared_group_and_reset_boundary(self):
        calls = []
        context = object()
        group = ParameterGroup(calls.append)
        mapping = [0, 0, 255]
        self.assertTrue(prepare_parameter(0, mapping, [group], context=context))
        self.assertFalse(prepare_parameter(1, mapping, [group], context=context))
        self.assertFalse(prepare_parameter(2, mapping, [group], context=context))
        reset_parameter_groups([group], enabled=False)
        self.assertFalse(prepare_parameter(0, mapping, [group]))
        reset_parameter_groups([group], enabled=True)
        self.assertTrue(prepare_parameter(1, mapping, [group], context=context))
        self.assertEqual(calls, [context, context])

    def test_flag_is_written_after_success(self):
        seen = []
        def callback(context):
            seen.append(group.prepared)
            raise RuntimeError('synthetic callback failure')
        group = ParameterGroup(callback)
        with self.assertRaises(RuntimeError):
            prepare_parameter(0, [0], [group])
        self.assertEqual(seen, [False])
        self.assertFalse(group.prepared)
        group.callback = lambda context: seen.append(group.prepared)
        prepare_parameter(0, [0], [group])
        self.assertTrue(group.prepared)
        self.assertEqual(seen, [False, False])

    def test_reset_clears_every_group(self):
        groups = [ParameterGroup(None, True), ParameterGroup(None, False)]
        reset_parameter_groups(groups, enabled=True)
        self.assertEqual([g.prepared for g in groups], [False, False])
        reset_parameter_groups([], enabled=True)

    def test_invalid_mapping_and_missing_callback(self):
        for index, mapping, groups in [(True, [0], []), (1, [255], []),
                                       (0, [256], []), (0, [1], []),
                                       (0, [0], [ParameterGroup(None)])]:
            with self.assertRaises(ValueError):
                prepare_parameter(index, mapping, groups)
