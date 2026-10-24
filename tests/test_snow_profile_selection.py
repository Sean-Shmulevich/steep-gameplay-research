import unittest
from engine.snow_profile_selection import accumulate_profile_volumes,select_volume_profile


class ContactProfileTests(unittest.TestCase):
    def test_volume_accumulation_is_not_positive_only(self):
        entries=accumulate_profile_volumes([
            dict(profile_key=10,volume=.75),dict(profile_key=20,volume=.5),
            dict(profile_key=10,volume=-.5)])
        self.assertEqual(select_volume_profile(entries)['profile_key'],20)

    def test_tie_uses_key_order_not_contribution_order(self):
        entries=accumulate_profile_volumes([
            dict(profile_key=2**63,volume=.5),dict(profile_key=10,volume=.5)])
        self.assertEqual(select_volume_profile(entries)['profile_key'],2**63)

    def test_empty_and_initial_minus_one_threshold(self):
        self.assertIsNone(select_volume_profile([])['profile_key'])
        self.assertIsNone(select_volume_profile([dict(profile_key=1,volume=-2)])['profile_key'])
        self.assertEqual(select_volume_profile([dict(profile_key=1,volume=-1)])['profile_key'],1)

    def test_duplicate_map_keys_require_explicit_accumulation(self):
        with self.assertRaises(ValueError):
            select_volume_profile([dict(profile_key=1,volume=0)]*2)
