"""Compare two brake tunings from one checkpoint through the controller HTTP API.

This command resets the addressed independent runtime. It uses simulated frames,
never wall-clock input duration, and saves both branches before restoring state.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from engine.replay import replay


def run(base_url, *, frames=30):
    parsed = urlparse(base_url)
    if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost')
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ('', '/')):
        raise ValueError('expected a loopback HTTP controller URL')
    if type(frames) is not int or not 1 <= frames <= 240:
        raise ValueError('frames must be 1..240 per segment')
    base_url = base_url.rstrip('/')

    def get(path):
        with urlopen(base_url+path, timeout=30) as response:
            return json.load(response)

    def command(**body):
        request = Request(base_url+'/command', data=json.dumps(body, allow_nan=False).encode(),
                          headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    def advance(token, actions):
        samples = []
        for index in range(frames):
            response = command(op='step_frame_once', token=token, dt=1/60, actions=actions)
            state = response['snapshot']['state']
            samples.append(dict(frame=index, tick=state['tick'], time=state['time'],
                                input_generation=state['input_generation'], body=state['body']))
        return samples

    def evidence():
        recording = get('/replay')
        trace = get('/trace')
        return dict(replay=recording,
                    replay_equal=replay(recording).state_hash() == recording['expected_hash'],
                    trace=trace, analysis=get('/trace/analysis'))

    reset = command(op='reset', scenario=dict(execution_mode='mixed',
        world={'slope': [-0.1, 0]}, trace={'capacity': 32000},
        scheduler={'mode': 'subdivision', 'smoothing_enabled': True}))
    token = reset['token']
    approach = advance(token, {'steer': .2})
    checkpoint = get('/checkpoint')
    approach_evidence = evidence()
    branches = []
    for name, deceleration in [('gentle', 2), ('strong', 12)]:
        token = command(op='restore', checkpoint=checkpoint)['token']
        token = command(op='tune', token=token,
                        changes={'physics': {'brake_deceleration': deceleration}})['token']
        start = get('/state')['state']
        samples = advance(token, {'brake': True})
        branches.append(dict(name=name, brake_deceleration=deceleration,
                             start=start, samples=samples, **evidence()))
    return dict(schema_version=1, scope='owned engine HTTP experiment; no native fidelity claim',
                frames_per_segment=frames, frame_dt=1/60, checkpoint=checkpoint,
                approach=dict(samples=approach, **approach_evidence), branches=branches,
                final_control=get('/state')['control'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8771')
    parser.add_argument('--frames', type=int, default=30)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = run(args.url, frames=args.frames)
    Path(args.output).write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    recordings = [report['approach'], *report['branches']]
    summary = dict(replay_equal=all(r['replay_equal'] for r in recordings),
                   trace_complete=all(r['trace']['complete'] for r in recordings),
                   paused=report['final_control']['paused'])
    print(json.dumps(summary))
    if not summary['replay_equal'] or not summary['trace_complete']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
