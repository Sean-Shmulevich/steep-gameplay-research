import copy
import unittest
from engine.animation import default_resources
from engine.graph import evaluate_pose
class PoseGraphTests(unittest.TestCase):
    def setUp(self):
        self.rig,self.clips=default_resources()
        self.nodes={'idle':{'type':'clip','clip':'idle'},'bend':{'type':'clip','clip':'bend'},'lean':{'type':'clip','clip':'lean','space':'delta'}}
    def run_graph(self,root,extra,state=None,dt=.5,inputs=None):
        return evaluate_pose(self.rig,self.clips,state or {},dt,{'schema_version':1,'root':root,'nodes':dict(self.nodes,**extra)},inputs or {})
    def test_order_and_dominant_ties(self):
        r=self.run_graph('mix',{'mix':{'type':'blend','children':['idle','bend'],'weights':[1,1]}})
        self.assertEqual(r['diagnostics']['contexts']['mix']['dominant_child'],'idle')
        self.assertEqual(r['diagnostics']['contexts']['mix']['order'],['idle','bend'])
        self.assertGreater(r['local_pose'][1]['quaternion_xyzw'][1],0)
    def test_zero_weight_child_clock_does_not_advance(self):
        r=self.run_graph('mix',{'mix':{'type':'blend','children':['idle','bend'],'weights':[1,0]}})
        self.assertNotIn('bend',r['state']['nodes'])
        self.assertEqual(r['state']['nodes']['idle']['time'],.5)
    def test_shared_child_evaluated_once(self):
        r=self.run_graph('mix',{'mix':{'type':'blend','children':['bend','bend'],'weights':[1,1]}})
        self.assertEqual(r['state']['nodes']['bend']['time'],.5)
        self.assertEqual(r['diagnostics']['visited'].count('bend'),1)
    def test_masks_and_exclusions(self):
        r=self.run_graph('mask',{'mask':{'type':'mask','base':'idle','overlay':'bend','bytes':{'knee':255,'unknown':0},'exclude':['rotation']}})
        self.assertEqual(r['local_pose'][1]['quaternion_xyzw'],[0,0,0,1])
        self.assertEqual(r['diagnostics']['unmatched_mask_bones'],['unknown'])
    def test_additive_requires_delta(self):
        r=self.run_graph('add',{'add':{'type':'additive','base':'idle','delta':'lean','weight':.5}})
        self.assertNotEqual(r['local_pose'][0]['quaternion_xyzw'],[0,0,0,1])
        with self.assertRaises(ValueError):self.run_graph('add',{'add':{'type':'additive','base':'idle','delta':'bend'}})
    def test_axial_and_selector(self):
        r=self.run_graph('axis',{'axis':{'type':'axial','children':['idle','bend'],'knots':[0,1],'coordinate':{'input':'steer'}}},inputs={'steer':1})
        self.assertEqual(r['diagnostics']['contexts']['axis']['left'],1)
        r=self.run_graph('s',{'s':{'type':'select','if_true':'bend','if_false':'idle','condition':{'input':'air'}}},inputs={'air':False})
        self.assertEqual(r['diagnostics']['contexts']['s']['selected'],'idle')
    def test_cycles_and_state_isolation(self):
        state={'nodes':{}}
        with self.assertRaises(ValueError):self.run_graph('s',{'s':{'type':'select','if_true':'s','if_false':'idle','condition':1}},state=state)
        self.assertEqual(state,{'nodes':{}})
    def test_checkpoint_continuation(self):
        node={'mix':{'type':'blend','children':['idle','bend'],'weights':[1,1]}}
        a=self.run_graph('mix',node,dt=.2);cp=copy.deepcopy(a['state'])
        b=self.run_graph('mix',node,state=a['state'],dt=.1);c=self.run_graph('mix',node,state=cp,dt=.1)
        self.assertEqual(b,c)

    def test_inactive_cycle_is_rejected(self):
        with self.assertRaises(ValueError):self.run_graph('idle',{'unused':{'type':'select','condition':0,'if_true':'unused','if_false':'idle'}})
