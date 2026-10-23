import unittest
from engine.command_executor import execute_commands


class CommandExecutorTests(unittest.TestCase):
    def setup_case(self, entries=()):
        manager = dict(executing_byte=7, array=0, count=len(entries), embedded='embedded')
        seen = []
        services = {name: (lambda receiver=None, name=name: seen.append(name))
                    for name in ('hierarchy', 'A', 'C', 'D', 'global')}
        services['B'] = lambda receiver: 1
        args = dict(services=services, read_slot=lambda i: entries[i],
                    invoke=lambda value: seen.append(value), read_global_flag=lambda: 0)
        return manager, seen, args

    def test_low_byte_and_short_circuit(self):
        for ready, flag, expected_c, reads in ((0, 0, True, 0), (256, 0, True, 0),
                                              (1, 0, False, 1), (1, 2, True, 1)):
            m, seen, args = self.setup_case(['p', 'p'])
            flags = []
            args['services']['B'] = lambda receiver: ready
            args['read_global_flag'] = lambda: flags.append(flag) or flag
            result = execute_commands(m, **args)
            self.assertEqual(seen, ['hierarchy', 'A'] + (['C'] if expected_c else []) + ['D', 'global', 'p', 'p'])
            self.assertEqual(len(flags), reads)
            self.assertEqual(result['callbacks'], 2)
            self.assertEqual(m['executing_byte'], 0)

    def test_append_and_swap_remove_have_live_iteration_effects(self):
        for operation, expected in [('append', ['a', 'b', 'c']), ('remove', ['a', 'b'])]:
            entries = ['a', 'b'] if operation == 'append' else ['a', 'b', 'c']
            m, seen, args = self.setup_case(entries)
            def invoke(value):
                seen.append(value)
                if value == 'a':
                    if operation == 'append': entries.append('c')
                    else: entries[0] = entries.pop()
                    m['count'] = len(entries)
            args['invoke'] = invoke
            execute_commands(m, **args)
            self.assertEqual(seen[4:], expected)

    def test_nested_return_clears_outer_flag(self):
        m, seen, args = self.setup_case(['p'])
        nested = False
        observed = []
        def invoke(value):
            nonlocal nested
            observed.append(m['executing_byte'])
            if not nested:
                nested = True
                execute_commands(m, **args)
                observed.append(m['executing_byte'])
        args['invoke'] = invoke
        execute_commands(m, **args)
        self.assertEqual(observed, [1, 1, 0])

    def test_relocated_end_does_not_rebase_cursor(self):
        m, seen, args = self.setup_case(['a', 'b', 'c'])
        def invoke(value):
            seen.append(value)
            m.update(array=2, count=1)
        args['invoke'] = invoke
        execute_commands(m, **args)
        self.assertEqual(seen[4:], ['a', 'b', 'c'])

    def test_exception_and_budget_do_not_invent_finally_cleanup(self):
        for budget in (0, 2):
            m, seen, args = self.setup_case(['p'])
            def invoke(value):
                raise LookupError('callback failed')
            args['invoke'] = invoke
            with self.assertRaises(RuntimeError if budget == 0 else LookupError):
                execute_commands(m, max_callbacks=budget, **args)
            self.assertEqual(m['executing_byte'], 1)


if __name__ == '__main__':
    unittest.main()
