#!/usr/bin/env python3
"""Exercise brake/boost against an already running synthetic Snow host only.

Never runs against the game adapter. Uses fixture-only binding handles.
"""
import argparse
import json
import math
from snow_host_client import SnowHostClient, speed_pulse


def probe(client):
    status = client.call('host.hello')
    if status.get('adapter') != 'fixture-simulated' or status.get('host_paused'):
        raise RuntimeError('Requires a running, unheld fixture-simulated host')
    checks = {}

    def refused(name, error, **params):
        r = client.request('player.adjust_speed', **params)
        checks[name] = r.get('status') == 'failed' and r.get('result', {}).get('error') == error

    def velocity(x, y=0, z=0):
        client.call('player.set_velocity', vx=x, vy=y, vz=z)

    def pulse(delta):
        return client.call('player.adjust_speed', delta_speed=delta)

    try:
        refused('requires_hold', 'not_paused_by_host', delta_speed=5)
        client.call('simulation.pause')
        client.call('player.bind', handle='fixture-player')
        refused('refuses_rotation', 'player_rotating', delta_speed=5)
        client.call('player.bind', handle='fixture-player-inactive')
        refused('refuses_inactive', 'player_not_in_world', delta_speed=5)
        client.call('player.bind', handle='fixture-player-straight')
        for delta in (0, 11, -11):
            refused(f'bad_delta_{delta}', 'bad_params', delta_speed=delta)
        refused('missing_delta', 'bad_params')
        refused('mixed_params', 'bad_params', delta_speed=5, vx=1)
        before = client.call('player.get')
        r = pulse(5)
        checks['boost'] = r['speed_before'] == 15 and r['speed_target'] == 20 and r['after']['linear_velocity'] == [20, 0, 0]
        checks['same_identity'] = before['identity'] == r['identity'] == r['after']['identity']
        r = pulse(-5)
        checks['brake'] = r['after']['linear_velocity'] == [15, 0, 0]
        velocity(3, 4, 0)
        checks['direction_preserved'] = pulse(5)['after']['linear_velocity'] == [6, 8, 0]
        velocity(-3, -4, 0)
        checks['negative_direction_preserved'] = pulse(5)['after']['linear_velocity'] == [-6, -8, 0]
        velocity(2)
        checks['stop_without_reverse'] = pulse(-5)['after']['linear_velocity'] == [0, 0, 0]
        refused('no_stationary_direction', 'direction_unresolved', delta_speed=5)
        velocity(58)
        checks['boost_cap'] = pulse(5)['after']['linear_velocity'] == [60, 0, 0]
        refused('cap_refusal', 'boost_speed_cap', delta_speed=5)
        velocity(80)
        checks['brake_above_cap'] = pulse(-5)['after']['linear_velocity'] == [75, 0, 0]
        velocity(15)
        r = pulse(5)
        pos = r['after']['position']
        client.call('simulation.step_world', count=1)
        after = client.call('player.get')
        checks['step_consumes_changed_velocity'] = math.isclose(after['position'][0] - pos[0], 20 / 60, abs_tol=1e-4)
        client.call('simulation.resume')
        r = speed_pulse(client, -5)
        checks['sample_client'] = r['ok'] and r['adjust']['after']['linear_velocity'] == [15, 0, 0]
        checks['sample_resumes'] = not client.call('simulation.status')['host_paused']
    finally:
        if client.call('simulation.status')['host_paused']:
            client.call('simulation.resume')
    return {'synthetic': True, 'passed': sum(checks.values()), 'total': len(checks), 'checks': checks, 'ok': all(checks.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=47017)
    args = parser.parse_args()
    with SnowHostClient(port=args.port) as client:
        result = probe(client)
    print(json.dumps(result, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
