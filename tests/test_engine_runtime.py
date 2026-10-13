import copy
import unittest
from engine.runtime import Engine,SPORTS
from engine.replay import record,replay
class RuntimeTests(unittest.TestCase):
    def test_sports_run(self):
        for sport in SPORTS:
            e=Engine({'sport':sport});e.step(240)
            self.assertEqual(e.state['tick'],240);self.assertEqual(e.incidents,[])
    def test_checkpoint_continuation(self):
        e=Engine();e.set_input({'steer':.4,'jump':True});e.step(80);checkpoint=e.checkpoint()
        e.set_input({'steer':-.2});e.step(100);expected=e.state_hash()
        e.restore(checkpoint);e.set_input({'steer':-.2});e.step(100)
        self.assertEqual(expected,e.state_hash())
    def test_replay(self):
        e=Engine();e.step(40);e.set_input({'jump':True});e.step(70);e.set_input({'flip':.5});e.step(200)
        other=replay(record(e));self.assertEqual(e.state_hash(),other.state_hash())
    def test_snapshot_isolation_pause(self):
        e=Engine();snapshot=e.snapshot();snapshot['body']['mass']=1
        self.assertEqual(e.state['body']['mass'],26);e.pause();e.step(3);self.assertEqual(e.state['tick'],0)
        e.pause(False);e.step();self.assertEqual(e.state['tick'],1)
    def test_invalid_load_does_not_erase_state(self):
        e=Engine();e.step(10);old=e.state_hash()
        with self.assertRaises(ValueError):e.load_scenario({'body':{'mass':-1}})
        self.assertEqual(old,e.state_hash())
    def test_fault_rolls_back_and_recovers(self):
        e=Engine();e.step(2);old=e.snapshot();original=e.world.sample
        e.world.sample=lambda *args: (_ for _ in ()).throw(ValueError('injected sensor failure'))
        with self.assertRaises(ValueError):e.step()
        self.assertTrue(e.state['paused']);self.assertEqual(e.state['body'],old['body']);self.assertEqual(len(e.incidents),1)
        e.world.sample=original;e.recover();e.step();self.assertEqual(e.state['tick'],3)
    def test_checkpoint_rejects_hash_tamper(self):
        e=Engine();cp=e.checkpoint();cp['scenario']['sport']='walking'
        with self.assertRaises(ValueError):e.restore(cp)
    def test_unknown_inputs_rejected(self):
        e=Engine()
        with self.assertRaises(ValueError):e.set_input({'undefined':1})

    def test_subdivision_replay(self):
        e=Engine({'scheduler':{'mode':'subdivision','policy':1}})
        for dt in (.01,.016,.025,.02):e.advance(dt)
        self.assertEqual(replay(record(e)).state_hash(),e.state_hash())
    def test_replay_after_restore(self):
        e=Engine();e.step(10);cp=e.checkpoint();e.step(10);e.restore(cp);e.step(5)
        self.assertEqual(replay(record(e)).state_hash(),e.state_hash())
    def test_advance_failure_is_transactional(self):
        e=Engine();e.step(2);old=e.state_hash()
        with self.assertRaises(ValueError):e.advance(float('nan'))
        self.assertEqual(old,e.state_hash())
    def test_paused_replay(self):
        e=Engine();e.step(2);e.pause()
        self.assertEqual(replay(record(e)).state_hash(),e.state_hash())

    def test_plane_contact_does_not_flicker(self):
        e=Engine()
        for _ in range(360):
            e.step();self.assertTrue(e.state['body']['grounded'])
        self.assertFalse(any(x['type']=='landing' for x in e.events))

    def test_air_landing_commits_once(self):
        e=Engine({'sport':'paraglider','world':{'slope':[0,0]},'body':{'position':[0,0,.1],'velocity':[0,0,-2]}})
        e.step(360)
        landings=[x for x in e.events if x['type']=='landing']
        self.assertEqual(len(landings),1);self.assertTrue(e.state['body']['grounded'])

    def test_gentle_curvature_contact(self):
        e=Engine({'world':{'slope':[0,0],'bumps':[{'center':[0,0],'height':.2,'radius':10}]},'body':{'position':[0,0,.2],'velocity':[1,0,0]}})
        for _ in range(240):e.step()
        self.assertFalse(any(x['type']=='landing' for x in e.events))

    def test_graph_scene_replay(self):
        definition={'schema_version':1,'root':'mix','nodes':{'idle':{'type':'clip','clip':'idle'},'bend':{'type':'clip','clip':'bend'},'mix':{'type':'blend','children':['idle','bend'],'weights':[1,{'input':'jump'}]}}}
        e=Engine({'animation':{'graph':definition}});e.step(10);e.set_input({'jump':True});e.step(40)
        self.assertIn('graph_state',e.state['animation']);self.assertIn('bend',e.state['pose']['diagnostics']['visited'])
        self.assertEqual(replay(record(e)).state_hash(),e.state_hash())
        cp=e.checkpoint();e.step(3);e.restore(cp);self.assertEqual(e.state,cp['state'])

    def test_resource_hot_reload_preserves_body_and_replays(self):
        from engine.animation import default_resources
        e=Engine();e.step(20);body=copy.deepcopy(e.state['body']);rig,clips=default_resources()
        rig['bones'][0]['local_bind']['translation'][2]=1.2
        e.replace_resources({'category':'synthetic','rig':rig,'clips':clips})
        self.assertEqual(body,e.state['body']);e.step(5)
        self.assertEqual(replay(record(e)).state_hash(),e.state_hash())
    def test_bad_resource_reload_is_transactional(self):
        e=Engine();old=e.state_hash()
        with self.assertRaises(ValueError):e.replace_resources({'category':'recovered_guess','rig':{},'clips':{}})
        self.assertEqual(old,e.state_hash())
    def test_tune_creates_reproducible_segment(self):
        e=Engine();e.step(50);before=e.snapshot();e.tune({'physics':{'brake_deceleration':4}})
        self.assertEqual(before,e.state);e.set_input({'brake':True});e.step(20)
        self.assertEqual(replay(record(e)).state_hash(),e.state_hash())
    def test_invalid_tune_does_not_mutate_state_or_scenario(self):
        e=Engine();before=e.checkpoint()
        with self.assertRaises(ValueError):e.tune({'physics':{'spring_mass':0}})
        self.assertEqual(before,e.checkpoint())
