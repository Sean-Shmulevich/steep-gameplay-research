import math
import unittest
from engine.rigid import box_cells,inertia,tensor,matvec
from engine.runtime import Engine
from engine.replay import record,replay
from reference.snow import tetra_volume
class RigidTests(unittest.TestCase):
    def test_volume_and_inertia(self):
        self.assertAlmostEqual(sum(tetra_volume(x) for x in box_cells([2,3,4])),24)
        diagonal=inertia([2,3,4],12);self.assertEqual(diagonal,[25,20,13])
        self.assertEqual(matvec(tensor([0,0,0,1],diagonal),[1,2,3]),[25,40,39])
    def test_cells_run_and_replay(self):
        e=Engine({'physics_mode':'rigid_cells'})
        e.step(360);e.set_input({'steer':.2,'jump':True});e.step(60);e.set_input({});e.step(180)
        self.assertEqual(e.state['diagnostics']['physics']['mode'],'rigid_cells')
        self.assertEqual(replay(record(e)).state_hash(),e.state_hash())
        self.assertEqual(e.incidents,[])
    def test_free_angular_momentum_conserved(self):
        e=Engine({'physics_mode':'rigid_cells','body':{'position':[0,0,100],'angular_velocity':[.2,.3,.4],'grounded':False},'rigid':{'gravity':0}})
        e.step();momentum=e.state['body']['_rigid']['angular_momentum'][:]
        e.step(240)
        self.assertEqual(momentum,e.state['body']['_rigid']['angular_momentum'])
        self.assertAlmostEqual(sum(x*x for x in e.state['body']['orientation']),1)
    def test_missing_control_domains_rejected(self):
        with self.assertRaises(ValueError):Engine({'sport':'walking','physics_mode':'rigid_cells'})
