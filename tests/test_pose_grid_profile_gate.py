import unittest
from engine.pose_grid_profile_gate import grid_triangle_profile_gate


class GridProfileGateTest(unittest.TestCase):
    def test_shared_cell_profile_and_either_direction_high_bits(self):
        resource=dict(default20='default',mapb0=[1],tablea0=['default','cell'])
        profiles={'default':dict(mask48=0,mask50=0),
                  'cell':dict(mask48=1<<60,mask50=0),
                  'other':dict(mask48=0,mask50=1<<60)}
        for triangle in (0,1):
            self.assertEqual(grid_triangle_profile_gate(resource,dict(default20='other'),triangle,profiles=profiles),('cell',True))
        profiles['cell']=dict(mask48=0,mask50=1<<63)
        profiles['other']=dict(mask48=1<<63,mask50=0)
        self.assertEqual(grid_triangle_profile_gate(resource,dict(default20='other'),0,profiles=profiles),('cell',True))

    def test_absent_map_falls_back_but_empty_present_map_does_not(self):
        profiles={'p':dict(mask48=1,mask50=2)}
        resource=dict(default20='p',mapb0=None,tablea0=[])
        self.assertEqual(grid_triangle_profile_gate(resource,dict(default20='p'),100,profiles=profiles),('p',False))
        resource['mapb0']=[]
        with self.assertRaises(IndexError):
            grid_triangle_profile_gate(resource,dict(default20='p'),0,profiles=profiles)
