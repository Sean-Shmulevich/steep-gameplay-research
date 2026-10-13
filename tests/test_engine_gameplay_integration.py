"""End-to-end checks of designed mixed dispatch against the direct runtime."""
import copy
import json
import unittest
from unittest.mock import patch

from engine import runtime
from engine.control import SchedulerController
from engine.replay import record, replay
from engine.runtime import Engine, SPORTS


class GameplayIntegrationTests(unittest.TestCase):
    def pair(self, sport, **options):
        scenario = dict(sport=sport, **options)
        return tuple(Engine(dict(scenario, execution_mode=mode))
                     for mode in ('direct', 'mixed'))

    def assert_numerical_parity(self, direct, mixed):
        self.assertEqual(direct.state_hash(), mixed.state_hash())
        self.assertEqual(direct.snapshot(), mixed.snapshot())
        for name in ('events', 'journal', 'commands', 'last_good'):
            self.assertEqual(getattr(direct, name), getattr(mixed, name), name)

    @staticmethod
    def exercise(engine):
        for actions, frame in (({'steer': .6, 'jump': True}, .025),
                               ({'steer': -.3, 'flip': .7, 'grab': True}, .017),
                               ({'brake': True, 'lean': -.4}, .011)):
            engine.set_input(actions)
            engine.advance(frame)
            engine.step(2)

    def test_all_sports_exact_parity_and_replay_with_distinct_scheduler_clocks(self):
        for sport in SPORTS:
            with self.subTest(sport=sport):
                direct, mixed = self.pair(sport, scheduler={'mode': 'subdivision'})
                self.exercise(direct)
                self.exercise(mixed)
                self.assert_numerical_parity(direct, mixed)
                for engine in (direct, mixed):
                    self.assertEqual(replay(record(engine)).state_hash(), engine.state_hash())
                records = mixed.trace.snapshot()['records']
                self.assertTrue(any(row['kind'] == 'gameplay_job' for row in records))
                enters = [row for row in records if row['kind'] == 'substep_enter']
                self.assertTrue(any(row['elapsed_dt'] != row['derivative_dt'] for row in enters))

    def test_all_sports_json_checkpoint_continuation_and_replay_base(self):
        for sport in SPORTS:
            with self.subTest(sport=sport):
                direct, mixed = self.pair(sport, scheduler={
                    'mode': 'subdivision', 'policy': 2,
                    'smoothing_enabled': True, 'history_capacity': 3})
                for engine in (direct, mixed):
                    self.exercise(engine)
                    checkpoint = json.loads(json.dumps(engine.checkpoint()))
                    self.exercise(engine)
                    expected = engine.state_hash()
                    expected_events = copy.deepcopy(engine.events)
                    engine.restore(checkpoint)
                    self.exercise(engine)
                    self.assertEqual(engine.state_hash(), expected)
                    self.assertEqual(engine.events, expected_events)
                    self.assertEqual(replay(record(engine)).state_hash(), expected)
                self.assert_numerical_parity(direct, mixed)

    def test_late_second_substep_failure_rolls_back_entire_outer_frame(self):
        for sport in SPORTS:
            engines = self.pair(sport, scheduler={'fixed_dt': .01})
            for engine in engines:
                with self.subTest(sport=sport, mode=engine.scenario['execution_mode']):
                    engine.step(2)
                    before = {name: copy.deepcopy(getattr(engine, name)) for name in
                              ('state', 'events', 'journal', 'commands', 'last_good')}
                    real_update = runtime.camera.update
                    calls = []

                    def fail_second(*args, **kwargs):
                        calls.append(1)
                        result = real_update(*args, **kwargs)
                        if len(calls) == 2:
                            raise RuntimeError('late second substep failure')
                        return result

                    with patch.object(runtime.camera, 'update', side_effect=fail_second):
                        with self.assertRaisesRegex(RuntimeError, 'late second'):
                            engine.advance(.035)
                    self.assertEqual(len(calls), 2)
                    for name, value in before.items():
                        self.assertEqual(getattr(engine, name), value, name)
                    self.assertEqual(len(engine.incidents), 1)
                    self.assertEqual(engine.trace.snapshot()['records'][-1]['kind'], 'frame_aborted')
                    engine.advance(.035)
                    self.assertEqual(replay(record(engine)).state_hash(), engine.state_hash())
            self.assert_numerical_parity(*engines)

    def test_controller_failed_frame_undoes_input_and_restores_owned_dispatch(self):
        controller = SchedulerController({'execution_mode': 'mixed', 'scheduler': {'fixed_dt': .01}})
        controller.submit_frame(.02, {'steer': .2})
        before = controller.checkpoint()
        with patch.object(runtime.camera, 'update', side_effect=RuntimeError('camera fault')):
            with self.assertRaisesRegex(RuntimeError, 'camera fault'):
                controller.submit_frame(.03, {'jump': True, 'steer': -.8})
        after = controller.checkpoint()
        self.assertEqual(after['engine']['state']['body'], before['engine']['state']['body'])
        for field in ('controls', 'input_generation', 'tick', 'scheduler'):
            self.assertEqual(after['engine']['state'][field], before['engine']['state'][field])
        self.assertEqual(after['engine']['journal'], before['engine']['journal'])
        self.assertEqual(after['engine_aux']['commands'], before['engine_aux']['commands'] +
                         [{'op': 'pause', 'value': True}])
        token = controller.pause()
        controller.step_frame_once(token, .02, {'steer': .7})
        expected = controller.snapshot()['state']
        recording = controller.export_replay()
        self.assertEqual(replay(recording).snapshot(), expected)
        # Restore into a different owner: no retained callback may mutate the source.
        checkpoint = json.loads(json.dumps(controller.checkpoint()))
        other = SchedulerController()
        other_token = other.restore(checkpoint)
        other.step_frame_once(other_token, .02, {'flip': .3})
        self.assertEqual(controller.snapshot()['state'], expected)
        controller.step_frame_once(token, .02, {'flip': .3})
        self.assertEqual(other.snapshot()['state'], controller.snapshot()['state'])

    def test_trace_overflow_cannot_change_physics_or_checkpoint_continuation(self):
        for sport in SPORTS:
            with self.subTest(sport=sport):
                direct, mixed = self.pair(sport, trace={'capacity': 1})
                self.exercise(direct)
                self.exercise(mixed)
                self.assert_numerical_parity(direct, mixed)
                self.assertGreater(mixed.trace.dropped, 0)
                self.assertFalse(mixed.trace.snapshot()['complete'])
                restored = Engine()
                restored.restore(json.loads(json.dumps(mixed.checkpoint())))
                mixed.step(3)
                restored.step(3)
                self.assertEqual(restored.state_hash(), mixed.state_hash())

    def test_zero_substep_frame_does_not_dispatch_gameplay(self):
        direct, mixed = self.pair('snowboard', scheduler={'fixed_dt': .01})
        for engine in (direct, mixed):
            engine.set_input({'jump': True})
            body = copy.deepcopy(engine.state['body'])
            engine.advance(.003)
            self.assertEqual(engine.state['tick'], 0)
            self.assertEqual(engine.state['body'], body)
            self.assertFalse(any(row['kind'] == 'gameplay_job'
                                 for row in engine.trace.snapshot()['records']))
            engine.advance(.009)
            self.assertEqual(engine.state['tick'], 1)
        self.assert_numerical_parity(direct, mixed)


if __name__ == '__main__':
    unittest.main()
