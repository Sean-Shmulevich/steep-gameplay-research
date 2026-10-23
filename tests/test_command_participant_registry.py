import unittest
from engine.command_participant_registry import register_participant,remove_participant

class RegistryTests(unittest.TestCase):
    def test_unique_append_and_duplicate_at_capacity(self):
        values=[10,20]
        self.assertEqual(register_participant(values,30,capacity=3)['entries'],[10,20,30])
        self.assertFalse(register_participant(values,10,capacity=2)['changed'])
        self.assertEqual(values,[10,20])
        with self.assertRaises(ValueError):register_participant(values,30,capacity=2)

    def test_removal_reorders_and_only_removes_first_match(self):
        self.assertEqual(remove_participant([10,20,30,40],20)['entries'],[10,40,30])
        self.assertEqual(remove_participant([10,20,10],10)['entries'],[10,20])
        self.assertFalse(remove_participant([],10)['changed'])
        self.assertFalse(remove_participant([10],20)['changed'])

    def test_membership_is_not_a_lifetime_guarantee(self):
        self.assertEqual(remove_participant([10],10)['entries'],[])
        for value in (-1,True,2**64):
            with self.assertRaises(ValueError):remove_participant([10],value)
