import unittest
from engine.action_refresh import reset_action, refresh_groups


class ActionRefreshTests(unittest.TestCase):
    def test_clear_before_evaluation_preserves_raw_and_status(self):
        original = bytes(range(160))
        seen = []
        def evaluate(value):
            seen.append(value)
            return value[:0x60] + b'\xff' * 16 + value[0x70:]
        result = reset_action(original, owner_suppressed=False, evaluate=evaluate)
        self.assertEqual(seen[0][0x60:0x84], bytes(0x24))
        self.assertEqual(seen[0][:0x60], original[:0x60])
        self.assertEqual(seen[0][0x84:], original[0x84:])
        self.assertEqual(result[0x60:0x70], b'\xff' * 16)
        self.assertEqual(result[0x30], original[0x30])
        self.assertEqual(original, bytes(range(160)))

    def test_suppression_clears_without_evaluation(self):
        result = reset_action(b'\xff' * 160, owner_suppressed=True,
                              evaluate=lambda _: self.fail('suppressed callback ran'))
        self.assertEqual(result[0x60:0x84], bytes(0x24))
        self.assertEqual(result[:0x60], b'\xff' * 0x60)

    def test_refresh_blocker_is_after_callback_and_group_local(self):
        events = []
        blocked = set()
        def reset(binding):
            events.append(('reset', binding))
            if binding == 'b': blocked.add(binding)
        def gate(binding):
            events.append(('gate', binding))
            return binding in blocked
        refresh_groups([['a', 'b', 'c'], ['d'], ['e', 'f']],
                       reset_binding=reset, blocker_enabled=gate)
        self.assertEqual(events, [(kind, b) for b in ['c', 'b', 'd', 'f', 'e']
                                  for kind in ['reset', 'gate']])

    def test_empty_groups_and_duplicate_identity(self):
        binding = object()
        seen = []
        refresh_groups([[], [binding, binding], []], reset_binding=seen.append,
                       blocker_enabled=lambda _: False)
        self.assertEqual(seen, [binding, binding])

    def test_callback_failure_is_not_neutral_input(self):
        def fail(_): raise RuntimeError('source unavailable')
        with self.assertRaisesRegex(RuntimeError, 'source unavailable'):
            reset_action(bytes(160), owner_suppressed=False, evaluate=fail)

    def test_invalid_adapter_inputs(self):
        with self.assertRaises(ValueError):
            reset_action(bytes(0x83), owner_suppressed=False, evaluate=lambda x: x)
        with self.assertRaises(ValueError):
            reset_action(bytes(160), owner_suppressed=1, evaluate=lambda x: x)
        with self.assertRaises(ValueError):
            reset_action(bytes(160), owner_suppressed=False, evaluate=lambda _: b'')
        with self.assertRaises(ValueError):
            refresh_groups([[]], reset_binding=lambda _: None, blocker_enabled=lambda _: False)


if __name__ == '__main__': unittest.main()
