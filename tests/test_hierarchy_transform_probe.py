import unittest
from engine.examples.hierarchy_transform_probe import run_probe


class HierarchyTransformProbeTests(unittest.TestCase):
    def test_parent_update_reaches_children_between_parent_notifications(self):
        result = run_probe()
        self.assertEqual(result['children']['0'][3], [9,11,13,1])
        self.assertEqual(result['children']['2'][3], [11,12,13,1])
        self.assertEqual(result['outgoing_flags'], {'0':29, '2':29})
        self.assertEqual(result['final_depths'], [0,0,0])
        self.assertEqual([(e['component'], e['phase']) for e in result['events']],
            [('parent-observer','pre'),('child-0','pre'),('child-0','post'),
             ('child-2','pre'),('child-2','post'),('parent-observer','post')])
