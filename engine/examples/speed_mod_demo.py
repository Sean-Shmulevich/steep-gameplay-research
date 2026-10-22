"""Runnable independent-engine brake/boost demo with exact local replay check.

Run: python3 -m engine.examples.speed_mod_demo
This uses synthetic resources and authored mod limits; no original game.
"""
import json
from engine.control import SchedulerController
from engine.replay import replay


def run():
    controller = SchedulerController({'body': {'velocity': [10, 0, 0]}})
    token = controller.pause()
    samples = []
    for delta in (2, -2):
        token = controller.adjust_speed(token, delta)
        state = controller.snapshot()['state']
        samples.append({'delta_speed': delta, 'tick': state['tick'],
                        'velocity': state['body']['velocity']})
    controller.step_once(token)
    controller.resume(token)
    for _ in range(60):
        controller.submit_frame(1/60)
    recording = controller.export_replay()
    restored = replay(recording)
    return {'scope': 'independent engine with synthetic resources', 'pulses': samples,
            'final_tick': restored.state['tick'], 'final_body': restored.state['body'],
            'replay_hash_matches': restored.state_hash() == recording['expected_hash']}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
