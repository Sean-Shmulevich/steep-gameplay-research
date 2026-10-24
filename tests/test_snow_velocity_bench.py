import json
from pathlib import Path
import unittest

from engine.snow_velocity_bench import inspect

EXAMPLE=Path(__file__).resolve().parents[1]/'engine/examples/snow_velocity_profile.json'


class VelocityBenchTests(unittest.TestCase):
    def doc(self):
        return json.loads(EXAMPLE.read_text())

    def test_profile_winner_changes_decay_without_mutating_input(self):
        doc=self.doc();before=json.dumps(doc)
        ordinary=inspect(doc)
        self.assertEqual(json.dumps(doc),before)
        self.assertEqual(ordinary['profile_selection']['profile_key'],10)
        doc['profile_volumes'][1]['volume']=1
        stronger=inspect(doc)
        self.assertEqual(stronger['profile_selection']['profile_key'],20)
        self.assertLess(stronger['correction']['selected']['velocity'][0],
                        ordinary['correction']['selected']['velocity'][0])

    def test_override_flag_reaches_speed_floor_selection(self):
        doc=self.doc();doc['velocity']['elapsed']=1;doc['velocity']['floor']=9
        normal=inspect(doc)
        self.assertEqual(normal['correction']['selected']['action'],'original_direction_at_floor')
        self.assertEqual(normal['correction']['selected']['velocity'][0],9)
        doc['drive']['override_value']=.5
        overridden=inspect(doc)
        self.assertEqual(overridden['correction']['selected']['action'],'candidate')
        self.assertLess(overridden['correction']['selected']['velocity'][0],9)

    def test_missing_winner_curve_and_null_do_not_get_fallback(self):
        doc=self.doc();doc['base_curves']=doc['base_curves'][1:]
        with self.assertRaises(ValueError):inspect(doc)
        doc=self.doc();doc['profile_volumes']=[]
        with self.assertRaises(ValueError):inspect(doc)

    def test_explicit_reachability_continuity_and_bounds(self):
        doc=self.doc();del doc['phase_continuity']
        with self.assertRaises(ValueError):inspect(doc)
        doc=self.doc();doc['bounds']={'lower':[-1]*3,'upper':[1]*3}
        with self.assertRaises(ValueError):inspect(doc)
        doc=self.doc();doc['stages_reached']=False;del doc['velocity']
        result=inspect(doc)
        self.assertEqual(result['status'],'not_evaluated')
        self.assertNotIn('correction',result)
