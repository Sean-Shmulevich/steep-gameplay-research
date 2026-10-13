"""Compare actual owned gameplay through direct and mixed phase dispatch.

Run: python3 -m engine.examples.gameplay_scheduler_probe
All terrain, inputs and phase topology are synthetic. No original game access.
"""
import json
from collections import Counter

from engine.runtime import Engine
from engine import replay


def run_probe():
    base = {
        'sport': 'snowboard',
        'scheduler': {'mode': 'subdivision', 'smoothing_enabled': True,
                      'history_capacity': 10, 'policy': 0},
        'trace': {'capacity': 16000},
        'world': {'slope': [-0.1, 0]},
    }
    direct = Engine(dict(base, execution_mode='direct'))
    mixed = Engine(dict(base, execution_mode='mixed'))
    intervals = [1/60] * 4 + [1/30, .08, 1/90, 1/120] + [1/60] * 4
    rows = []
    checkpoint = None
    for frame, dt in enumerate(intervals):
        actions = {'steer': .3} if frame < 4 else {'jump': frame == 4, 'flip': .2}
        for engine in (direct, mixed):
            engine.set_input(actions)
            engine.advance(dt)
        assert direct.state_hash() == mixed.state_hash(), frame
        assert direct.events == mixed.events, frame
        rows.append({'frame': frame, 'dt': dt, 'tick': mixed.state['tick'],
                     'state_hash': mixed.state_hash()})
        if frame == 5:
            checkpoint = mixed.checkpoint()
    restored = Engine()
    restored.restore(checkpoint)
    for frame in range(6, len(intervals)):
        restored.set_input({'jump': False, 'flip': .2})
        restored.advance(intervals[frame])
    assert restored.state_hash() == mixed.state_hash()
    replayed = replay.replay(replay.record(mixed))
    assert replayed.state_hash() == mixed.state_hash()
    trace = mixed.trace.snapshot()
    assert trace['complete']
    jobs = [row for row in trace['records'] if row['kind'] == 'gameplay_job']
    reservations = Counter(row['job'] for row in jobs if row['job_event'] == 'mixed_dispatch_reserved')
    expected = {phase: mixed.state['tick'] for phase in ('physics', 'environment', 'scoring', 'animation', 'camera')}
    assert dict(reservations) == expected, reservations
    assert sum(row['job_event'] == 'mixed_terminal_begin' and row['job'] == 'ready' for row in jobs) == mixed.state['tick']
    return {
        'scope': 'Owned gameplay with synthetic phase topology; not native execution parity',
        'frames': rows,
        'direct_mixed_state_equal': True,
        'checkpoint_continuation_equal': True,
        'replay_equal': True,
        'phase_dispatches': dict(reservations),
        'trace_records': trace['attempted'],
        'trace_dropped': trace['dropped'],
        'incidents': mixed.incidents,
    }


if __name__ == '__main__':
    print(json.dumps(run_probe(), indent=2))
