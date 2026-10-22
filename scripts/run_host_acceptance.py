#!/usr/bin/env python3
"""Run bounded pause/step/brake/boost checks on an already running Snow host.

No launcher, game files, screenshots or synthetic motion are supplied here.
The player must already be bound, moving, and eligible for the speed trial.
"""
import argparse
import json
from pathlib import Path

from host_acceptance import run_acceptance
from snow_host_client import SnowHostClient
from speed_acceptance import run_speed_acceptance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=47017)
    parser.add_argument('--steps', type=int, default=3)
    parser.add_argument('--output', type=Path, help='Optional private JSON receipt')
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('--port must be from 1 to 65535')
    if not 1 <= args.steps <= 60:
        parser.error('--steps must be from 1 to 60')
    report = {'ok': False, 'scope': 'already-running host command acceptance',
              'startup_tested': False, 'visual_behavior_tested': False,
              'captures': []}

    def no_forward_input():
        raise RuntimeError('Player is not speed-trial eligible. Move onto a clear slope '
                           'and rerun; this command does not inject movement input.')

    try:
        with SnowHostClient(port=args.port) as client:
            def capture(label):
                report['captures'].append({'label': label, 'player': client.call('player.get')})
            result = run_acceptance(client, lambda: run_speed_acceptance(
                client, capture, no_forward_input), steps=args.steps)
            report.update(result)
    except Exception as exc:
        report['error'] = str(exc)
    payload = json.dumps(report, indent=2, allow_nan=False) + '\n'
    print(payload, end='')
    if args.output:
        args.output.write_text(payload)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
