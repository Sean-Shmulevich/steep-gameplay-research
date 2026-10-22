#!/usr/bin/env python3
"""Client for the Snow mod host command channel (native/snow_host).

Library:
    with SnowHostClient(port=47017) as host:
        host.call('simulation.pause', lease_ms=30000)
        host.call('simulation.step_world', count=1)
        host.call('simulation.resume')

CLI:
    snow_host_client.py status | pause [--lease-ms N] | step [N] | resume | demo [--steps N]
                        | player [--bind HANDLE]

Each request receives an 'accepted' line, then exactly one 'completed' or
'failed' line; malformed or unknown requests receive one 'rejected' line.
A host-held pause is released automatically when its lease expires or this
connection closes, so a pause only lasts as long as the client is connected.
"""
import argparse
import json
import math
import socket
import sys
import time

DEFAULT_PORT = 47017


class HostError(RuntimeError):
    def __init__(self, response):
        self.response = response
        result = response.get('result') or {}
        super().__init__(f"{response.get('status')}: {result.get('error') or response.get('error')}")


class SnowHostClient:
    def __init__(self, host='127.0.0.1', port=DEFAULT_PORT, timeout=10.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.timeout = timeout
        self.buffer = b''
        self.next_id = 1

    def close(self):
        self.sock.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _line(self, deadline):
        while b'\n' not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('No response from host')
            self.sock.settimeout(remaining)
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError('Host closed the connection')
            self.buffer += chunk
        line, self.buffer = self.buffer.split(b'\n', 1)
        return json.loads(line)

    def request(self, method, **params):
        """Send one request; return the final response dict without raising on failure."""
        rid = self.next_id
        self.next_id += 1
        message = {'id': rid, 'method': method}
        if params:
            message['params'] = params
        self.sock.sendall(json.dumps(message, separators=(',', ':')).encode() + b'\n')
        # Stepping may legitimately take up to ~3 s per step on the host side.
        deadline = time.monotonic() + self.timeout + 3.0 * params.get('count', 1)
        first = self._line(deadline)
        if first.get('id') != rid:
            raise ConnectionError(f'Out-of-order response: {first}')
        if first.get('status') != 'accepted':
            return first
        final = self._line(deadline)
        if final.get('id') != rid or final.get('status') not in ('completed', 'failed'):
            raise ConnectionError(f'Unexpected final response: {final}')
        return final

    def call(self, method, **params):
        """Send one request; return its result or raise HostError."""
        response = self.request(method, **params)
        if response.get('status') != 'completed':
            raise HostError(response)
        return response['result']


def demo(client, steps, lease_ms):
    """Bounded pause/step/resume transaction; never take over an existing hold.

    A lost mutation response is not retried. Resume is attempted even when the
    pause result is uncertain; disconnect/lease recovery remains the fallback.
    """
    if type(steps) is not int or not 1 <= steps <= 60:
        raise ValueError('steps must be an integer from 1 to 60')
    if type(lease_ms) is not int or not 1000 <= lease_ms <= 300000:
        raise ValueError('lease_ms must be an integer from 1000 to 300000')
    record = {'ok': False, 'steps': []}
    try:
        record['before'] = client.call('simulation.status')
        if record['before'].get('host_paused'):
            raise RuntimeError('Already held; refusing to resume an existing pause')
        try:
            record['pause'] = client.call('simulation.pause', lease_ms=lease_ms)
            for _ in range(steps):
                step = client.call('simulation.step_world', count=1)
                record['steps'].append({'step': step})
                if step.get('exactly_one') != 1:
                    raise RuntimeError('World-step result did not confirm exactly one execution')
                status = client.call('simulation.status')
                record['steps'][-1]['status'] = status['engine']
            record['ok'] = True
        finally:
            try:
                record['resume'] = client.request('simulation.resume')
                if record['resume'].get('status') != 'completed':
                    record['ok'] = False
            except Exception as exc:
                record['resume_error'] = str(exc)
                record['ok'] = False
    except Exception as exc:
        record['error'] = str(exc)
    # Preserve partial evidence if recovery or the final read fails.
    if 'pause' in record or 'resume' in record or 'resume_error' in record:
        try:
            record['after'] = client.call('simulation.status')
            if record['after'].get('host_paused'):
                record['ok'] = False
                record['recovery_error'] = 'Host still reports a held simulation'
        except Exception as exc:
            record['after_error'] = str(exc)
            record['ok'] = False
    return record


def speed_pulse(client, delta_speed):
    """One engine-routine brake/boost pulse. Always attempt to release our hold.

    Direction and speed are calculated inside the host, not from client reads.
    No automatic retry: a lost response can follow a successful mutation.
    """
    if not math.isfinite(delta_speed) or not 0 < abs(delta_speed) <= 10:
        raise ValueError('Speed change must be finite, nonzero, and at most 10 units/s')
    record = {'ok': False, 'delta_speed': delta_speed}
    try:
        status = client.call('simulation.status')
        if status.get('host_paused'):
            raise RuntimeError('Already held; refusing to resume an existing pause')
        # From here even a pause timeout needs a resume attempt; the host may
        # have accepted it. Disconnect/lease recovery remains the fallback.
        try:
            record['pause'] = client.call('simulation.pause', lease_ms=10000)
            record['adjust'] = client.call('player.adjust_speed', delta_speed=delta_speed)
            record['ok'] = True
        finally:
            try:
                record['resume'] = client.request('simulation.resume')
                if record['resume'].get('status') != 'completed':
                    record['ok'] = False
            except Exception as exc:
                record['resume_error'] = str(exc)
                record['ok'] = False
    except Exception as exc:
        record['error'] = str(exc)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    pause = sub.add_parser('pause', help='Pause and hold while connected (Ctrl+C resumes)')
    pause.add_argument('--lease-ms', type=int, default=30000)
    step = sub.add_parser('step', help='Pause, step N world steps, resume')
    step.add_argument('count', type=int, nargs='?', default=1)
    sub.add_parser('resume')
    for action in ('boost', 'brake'):
        pulse = sub.add_parser(action, help='One bounded speed pulse through the engine routine; pause then resume')
        pulse.add_argument('--amount', type=float, default=5.0, help='Positive speed change, at most 10 world units/s')
    pl = sub.add_parser('player', help='Read the bound player (bind first with --bind HANDLE)')
    pl.add_argument('--bind', metavar='HANDLE', help='opaque handle from an external acquisition')
    d = sub.add_parser('demo', help='Pause, step and record status, resume')
    d.add_argument('--steps', type=int, default=5)
    d.add_argument('--lease-ms', type=int, default=30000)
    args = parser.parse_args(argv)

    if args.command in ('step', 'demo'):
        count = args.count if args.command == 'step' else args.steps
        if not 1 <= count <= 60:
            parser.error('step count must be from 1 to 60')
    with SnowHostClient(args.host, args.port) as client:
        if args.command == 'status':
            out = client.request('simulation.status')
        elif args.command == 'pause':
            out = client.request('simulation.pause', lease_ms=args.lease_ms)
            print(json.dumps(out), flush=True)
            if out.get('status') != 'completed':
                return 1
            print('Held. Press Enter (or Ctrl+C) to resume.', file=sys.stderr, flush=True)
            try:
                # Heartbeats renew the lease while we wait.
                import select
                while not select.select([sys.stdin], [], [], args.lease_ms / 3000)[0]:
                    client.call('host.heartbeat')
            except KeyboardInterrupt:
                pass
            out = client.request('simulation.resume')
        elif args.command == 'step':
            out = demo(client, args.count, 30000)
        elif args.command == 'player':
            out = {}
            if args.bind:
                out['bind'] = client.request('player.bind', handle=args.bind)
            out['get'] = client.request('player.get')
        elif args.command in ('boost', 'brake'):
            if not math.isfinite(args.amount) or not 0 < args.amount <= 10:
                parser.error('--amount must be finite, positive and at most 10')
            out = speed_pulse(client, args.amount if args.command == 'boost' else -args.amount)
        elif args.command == 'resume':
            out = client.request('simulation.resume')
        else:
            out = demo(client, args.steps, args.lease_ms)
    print(json.dumps(out, indent=1))
    if args.command == 'player':
        ok = all(r.get('status') == 'completed' for r in out.values())
    else:
        ok = out.get('ok', out.get('status') == 'completed')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
