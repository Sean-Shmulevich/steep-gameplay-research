import unittest
from engine.kino_activation import plan_kino_activation
from engine.event_registry import WorldEventRegistry


class KinoActivationTests(unittest.TestCase):
    def test_enable_routes_and_auxiliary_dirty_bit(self):
        for grouped in (False, True):
            for bit in (False, True):
                result = plan_kino_activation(requested=True, active=False,
                    group_contains_owner=grouped, owner_flags=(1 << 36) if bit else 0,
                    auxiliary_present=True, auxiliary_flags=0x40)
                self.assertEqual([e['slot'] for e in result['events']],
                    ([] if grouped else [16]) + [37 if bit else 19, 17])
                self.assertTrue(result['active'])
                self.assertEqual(result['auxiliary_flags'], 0x240)

    def test_disable_removes_both_route_variants(self):
        registry = WorldEventRegistry()
        for slot in (16, 37, 19, 17):
            registry.register(slot, 100)
        result = plan_kino_activation(requested=False, active=True, component_flags=0xff)
        self.assertEqual(result['events'][0], {'operation': 'interface_140'})
        for event in result['events']:
            if event['operation'] == 'remove':
                registry.remove(event['slot'], 100)
        self.assertEqual([registry.snapshot(s) for s in (16, 37, 19, 17)], [[], [], [], []])
        self.assertFalse(result['active'])
        self.assertEqual(result['component_flags'], 0xfe)
        self.assertEqual(result['events'][-1], {'operation': 'post_unregister', 'argument': 0.20000000298023224})

    def test_missing_world_and_repeated_disable(self):
        result = plan_kino_activation(requested=False, active=True,
                                     world_present=False, component_flags=3)
        self.assertTrue(result['active'])
        self.assertEqual(result['component_flags'], 2)
        self.assertEqual(result['events'], [{'operation': 'interface_140'}])
        result = plan_kino_activation(requested=False, active=False)
        self.assertEqual(result['events'], [{'operation': 'interface_140'}])
        self.assertEqual(plan_kino_activation(requested=True, active=True)['events'], [])
        self.assertFalse(plan_kino_activation(requested=True, active=False,
                                             owner_is_sentinel=True)['active'])

    def test_observation_widths(self):
        for fields in ({'owner_flags': -1}, {'component_flags':256},
                       {'auxiliary_flags':65536}, {'world_present':1}):
            with self.assertRaises(ValueError):
                plan_kino_activation(requested=True, active=False, **fields)
