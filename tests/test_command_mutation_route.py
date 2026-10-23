import unittest
from engine.command_mutation_route import select_command_mutation_route

class CommandMutationRouteTests(unittest.TestCase):
    def test_reentrancy_and_participant_bypass(self):
        for active in (0,1,2,255):
            self.assertEqual(select_command_mutation_route(active,0),'defer' if active else 'immediate')
            for bypass in (1,2,255):
                self.assertEqual(select_command_mutation_route(active,bypass),'immediate')

    def test_no_implicit_flag_coercion(self):
        for value in (-1,256,True,0.0,None):
            with self.assertRaises(ValueError):select_command_mutation_route(value,0)
            with self.assertRaises(ValueError):select_command_mutation_route(0,value)
