"""Joint reconstructed contact/animation/mod integration; synthetic hull and rig."""
import json
from pathlib import Path
import unittest
from engine.control import SchedulerController
from engine.replay import replay


class RigidAnimationModTests(unittest.TestCase):
    def test_both_snow_sports_replay_and_preserve_momentum_at_speed_mutation(self):
        for sport in ('snowboard','ski'):
            with self.subTest(sport=sport):
                scene=json.loads((Path(__file__).resolve().parents[1]/'engine/examples/byte_pose_graph.json').read_text())
                scene.update(sport=sport,physics_mode='rigid_cells',execution_mode='mixed',
                             scheduler={'mode':'subdivision'},body={'velocity':[10,0,0]})
                controller=SchedulerController(scene);token=controller.pause()
                controller.step_frame_once(token,.02,{'steer':.2},include_trace=False)
                before=controller.snapshot(include_trace=False)['state']
                self.assertGreater(before['diagnostics']['physics']['submerged_volume'],0)
                self.assertTrue(any(before['diagnostics']['physics']['pressure_impulse']))
                token=controller.adjust_speed(token,2)
                after=controller.snapshot(include_trace=False)['state']
                self.assertEqual(after['body']['_rigid']['angular_momentum'],before['body']['_rigid']['angular_momentum'])
                self.assertEqual(after['body']['angular_velocity'],before['body']['angular_velocity'])
                self.assertEqual(after['pose'],before['pose'])
                for actions in ({'jump':True},{'lean':.3},{'brake':True}):
                    controller.step_frame_once(token,.02,actions,include_trace=False)
                final=controller.snapshot(include_trace=False)['state']
                self.assertEqual(final['diagnostics']['physics']['mode'],'rigid_cells')
                self.assertEqual(final['pose']['diagnostics']['contexts']['masked']['operation'],'masked')
                self.assertEqual(replay(controller.export_replay()).snapshot(),final)
