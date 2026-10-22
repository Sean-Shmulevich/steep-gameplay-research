"""Loopback HTTP adapter exclusively owning an independent SchedulerController."""
import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math

from .control import PauseToken, SchedulerController
from .trace_analysis import analyze


def decode_token(value):
    if not isinstance(value, dict) or set(value) != {'controller_id', 'generation', 'pause_serial'}:
        raise ValueError('invalid pause token schema')
    identity = value['controller_id']
    if type(identity) is not str or len(identity) != 32 or any(c not in '0123456789abcdef' for c in identity):
        raise ValueError('invalid controller identity')
    for key in ('generation', 'pause_serial'):
        if type(value[key]) is not int or value[key] < 0:
            raise ValueError('invalid pause token counter')
    return PauseToken(**value)


def _frame_dt(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('frame interval must be in [0,1] seconds')
    return value


def make_server(port=8771, scenario=None):
    controller = SchedulerController(scenario)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, value, status=200):
            data = json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == '/state':
                self.send(controller.snapshot())
            elif self.path == '/state?trace=summary':
                self.send(controller.snapshot(include_trace=False))
            elif self.path == '/checkpoint':
                self.send(controller.checkpoint())
            elif self.path == '/replay':
                self.send(controller.export_replay())
            elif self.path in ('/trace', '/trace/analysis'):
                trace = controller.snapshot()['trace']
                self.send(trace if self.path == '/trace' else analyze(trace))
            else:
                self.send(dict(error='Not found'), 404)

        def do_POST(self):
            if self.path != '/command':
                self.send(dict(error='Not found'), 404)
                return
            origin = self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',
                                         f'http://localhost:{self.server.server_port}'):
                self.send(dict(error='Cross-origin mutation rejected'), 403)
                return
            include_trace = True
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 2_000_000:
                    raise ValueError('invalid request size')
                request = json.loads(self.rfile.read(length))
                if not isinstance(request, dict):
                    raise ValueError('command must be an object')
                requested_trace = request.get('include_trace', True)
                if type(requested_trace) is not bool:
                    raise ValueError('include_trace must be boolean')
                include_trace = requested_trace
                op = request.get('op')
                token = None
                if op == 'pause':
                    token = controller.pause()
                elif op == 'reset':
                    token = controller.reset(request.get('scenario'))
                elif op == 'restore':
                    token = controller.restore(request['checkpoint'])
                elif op == 'submit_frame':
                    controller.submit_frame(_frame_dt(request['dt']), request.get('actions'), include_trace=False)
                elif op in ('resume', 'step_once', 'step_frame_once', 'tune', 'replace_resources', 'adjust_speed', 'apply_central_impulse'):
                    supplied = decode_token(request['token'])
                    if op == 'resume':
                        controller.resume(supplied)
                    elif op == 'step_once':
                        controller.step_once(supplied, request.get('actions'), include_trace=False)
                        token = supplied
                    elif op == 'step_frame_once':
                        controller.step_frame_once(supplied, _frame_dt(request['dt']), request.get('actions'), include_trace=False)
                        token = supplied
                    elif op == 'apply_central_impulse':
                        token = controller.apply_central_impulse(supplied, request['impulse'])
                    elif op == 'adjust_speed':
                        token = controller.adjust_speed(supplied, request['delta_speed'])
                    elif op == 'tune':
                        token = controller.tune(supplied, request['changes'])
                    else:
                        token = controller.replace_resources(supplied, request['bundle'])
                else:
                    raise ValueError('unknown controller operation')
                self.send(dict(snapshot=controller.snapshot(include_trace=include_trace), token=asdict(token) if token else None))
            except (ValueError, KeyError, TypeError, ArithmeticError, RuntimeError) as exc:
                self.send(dict(error=str(exc), snapshot=controller.snapshot(include_trace=include_trace)), 400)

    # Single request dispatch prevents a command's response snapshot being
    # interleaved with another HTTP command. No direct Engine handle is exposed.
    return HTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8771)
    args = parser.parse_args()
    server = make_server(args.port)
    print(f'Owned scheduler API: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
