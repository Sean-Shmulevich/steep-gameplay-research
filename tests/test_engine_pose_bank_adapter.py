"""Runtime integration of recovered arithmetic under an authored bank layout."""
import copy
import math
import struct
import unittest
from engine.pose_bank_adapter import blend_pose
from engine.runtime import Engine
from engine.replay import record, replay

POLICY='authored_exact_sqrt'
GRAPH={'schema_version':1,'root':'mix','nodes':{
    'idle':{'type':'clip','clip':'idle'},
    'bend':{'type':'clip','clip':'bend'},
    'mix':{'type':'byte_blend','base':'idle','overlay':'bend',
           'weight':.5,'normalization':POLICY}}}

class PoseBankAdapterTests(unittest.TestCase):
    def test_translation_rotation_and_near_one_copy(self):
        a=[dict(translation=[0,2,4],quaternion_xyzw=[0,0,0,1])]
        b=[dict(translation=[4,6,8],quaternion_xyzw=[0,math.sin(.4),0,math.cos(.4)])]
        before=copy.deepcopy((a,b))
        result,info=blend_pose(a,b,.5,normalization=POLICY)
        self.assertEqual(result[0]['translation'],[2,4,6])
        self.assertGreater(result[0]['quaternion_xyzw'][1],0)
        self.assertAlmostEqual(sum(x*x for x in result[0]['quaternion_xyzw']),1,places=5)
        copied,info=blend_pose(a,b,1,normalization=POLICY)
        self.assertEqual(info['visits'][0]['helper'],'copy_second')
        self.assertEqual(copied[0]['quaternion_xyzw'],list(struct.unpack('<4f',struct.pack('<4f',*b[0]['quaternion_xyzw']))))
        self.assertEqual((a,b),before)

    def test_graph_runs_and_replays_with_diagnostics(self):
        e=Engine({'animation':{'graph':GRAPH}})
        e.set_input({'steer':.2});e.step(25)
        context=e.state['pose']['diagnostics']['contexts']['mix']
        self.assertEqual(context['normalization'],POLICY)
        self.assertIn('authored',context['layout'])
        self.assertEqual(context['visits'][0]['count'],len(e.rig['bones'])*2)
        self.assertEqual(replay(record(e)).snapshot(),e.snapshot())
        checkpoint=e.checkpoint();e.step(3);expected=e.snapshot()
        e.restore(checkpoint);e.step(3);self.assertEqual(e.snapshot(),expected)

    def test_missing_policy_rejected_even_in_inactive_branch(self):
        graph=copy.deepcopy(GRAPH);del graph['nodes']['mix']['normalization']
        graph['root']='idle'
        with self.assertRaises(ValueError):Engine({'animation':{'graph':graph}})
        with self.assertRaises(ValueError):blend_pose([],[],.5,normalization='hardware_guess')

    def test_additive_weight_and_unweighted_branch_preserve_base_order(self):
        a=[dict(translation=[10,20,30],quaternion_xyzw=[0,0,0,1])]
        b=[dict(translation=[2,4,6],quaternion_xyzw=[0,math.sin(.4),0,math.cos(.4)])]
        result,info=blend_pose(a,b,.5,normalization=POLICY,operation='additive')
        self.assertEqual(result[0]['translation'],[11,22,33])
        self.assertEqual(info['sources'],['base','delta'])
        result,info=blend_pose(a,b,1,normalization=POLICY,operation='additive')
        self.assertEqual(result[0]['translation'],[12,24,36])
        self.assertEqual(info['visits'][0]['helper'],'unweighted_combine')
        self.assertAlmostEqual(result[0]['quaternion_xyzw'][1],math.sin(.4),places=6)

    def test_additive_graph_runtime_replay_and_space_guard(self):
        graph=copy.deepcopy(GRAPH)
        graph['nodes']['lean']={'type':'clip','clip':'lean','space':'delta'}
        graph['nodes']['layer']={'type':'byte_additive','base':'mix','delta':'lean',
                                'weight':.5,'normalization':POLICY}
        graph['root']='layer'
        e=Engine({'animation':{'graph':graph}});e.step(60)
        self.assertEqual(e.state['pose']['diagnostics']['contexts']['layer']['operation'],'additive')
        self.assertEqual(replay(record(e)).snapshot(),e.snapshot())
        graph['nodes']['lean']['space']='local'
        with self.assertRaises(ValueError):Engine({'animation':{'graph':graph}})

    def test_masked_bytes_control_translation_and_rotation_per_bone(self):
        a=[dict(translation=[0,0,0],quaternion_xyzw=[0,0,0,1]) for _ in range(3)]
        b=[dict(translation=[255,0,0],quaternion_xyzw=[0,math.sin(.4),0,math.cos(.4)]) for _ in range(3)]
        result,info=blend_pose(a,b,1,normalization=POLICY,operation='masked',mask_bytes=[0,128,255])
        self.assertEqual(result[0],a[0])
        self.assertAlmostEqual(result[1]['translation'][0],128,places=4)
        self.assertEqual(result[2]['translation'],b[2]['translation'])
        self.assertGreater(result[1]['quaternion_xyzw'][1],0)
        self.assertLess(result[1]['quaternion_xyzw'][1],result[2]['quaternion_xyzw'][1])
        self.assertEqual(info['mask_bytes'],[0,128,255])
        with self.assertRaises(ValueError):
            blend_pose(a,b,1,normalization=POLICY,operation='masked',mask_bytes=[True,128,255])

    def test_masked_graph_runs_replays_and_reports_unmatched_bones(self):
        graph=copy.deepcopy(GRAPH)
        graph['nodes']['mix'].update(type='byte_mask',bytes={'knee':255,'missing':128})
        e=Engine({'animation':{'graph':graph}});e.step(30)
        self.assertEqual(e.state['pose']['diagnostics']['unmatched_mask_bones'],['missing'])
        self.assertEqual(replay(record(e)).snapshot(),e.snapshot())
        graph['nodes']['mix']['bytes']['knee']=256
        graph['root']='idle'
        with self.assertRaises(ValueError):Engine({'animation':{'graph':graph}})

    def test_boolean_control_weight_drives_copy_branch(self):
        graph=copy.deepcopy(GRAPH)
        graph['nodes']['mix']['weight']={'input':'jump'}
        engine=Engine({'animation':{'graph':graph}})
        engine.set_input({'jump':True});engine.step(1)
        context=engine.state['pose']['diagnostics']['contexts']['mix']
        self.assertEqual(context['visits'][0]['helper'],'copy_second')
        engine.set_input({'jump':False});engine.step(1)
        self.assertEqual(replay(record(engine)).snapshot(),engine.snapshot())
