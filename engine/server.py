"""Loopback JSON testbench and browser inspector; one shared simulation."""
import json
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from .runtime import Engine
from .replay import record
from .inspection import inspect_rig

def make_server(port=8770,scenario=None):
    engine=Engine(scenario); saved={}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,value,status=200,content_type='application/json'):
            data=value if isinstance(value,bytes) else json.dumps(value,allow_nan=False).encode()
            self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if self.path=='/':self.send(Path(__file__).with_name('view.html').read_bytes(),content_type='text/html; charset=utf-8')
            elif self.path=='/state':self.send(engine.snapshot())
            elif self.path=='/resources':self.send(dict(rig=engine.rig,category=engine.scenario.get('resources',{}).get('category','synthetic'),inspection=inspect_rig(engine.rig,engine.clips),world=engine.world.to_dict()))
            elif self.path=='/replay':self.send(record(engine))
            elif self.path=='/trace':self.send(engine.trace.snapshot())
            else:self.send({'error':'Not found'},404)
        def do_POST(self):
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
                self.send({'error':'Cross-origin mutation rejected'},403);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=2_000_000:raise ValueError('Invalid request size')
                req=json.loads(self.rfile.read(length));op=req.get('op')
                if op=='input':engine.set_input(req['actions'])
                elif op=='advance':
                    dt=req['dt']
                    if isinstance(dt,bool) or not isinstance(dt,(int,float)) or not math.isfinite(dt) or not 0<=dt<=1:
                        raise ValueError('Request frame interval must be in [0,1] seconds')
                    engine.advance(dt)
                elif op=='step':
                    count=req.get('count',1)
                    if type(count) is not int or not 0<=count<=2400:raise ValueError('Request step limit is 2400')
                    engine.step(count)
                elif op=='run':
                    count=req.get('count',4)
                    if type(count) is not int or not 0<=count<=2400:raise ValueError('Request step limit is 2400')
                    engine.set_input(req.get('actions',{}));engine.step(count)
                elif op=='pause':engine.pause(req.get('value',True))
                elif op=='reset':engine.load_scenario(req.get('scenario',engine.scenario))
                elif op=='checkpoint':saved['checkpoint']=engine.checkpoint()
                elif op=='restore':engine.restore(saved['checkpoint'])
                elif op=='recover':engine.recover()
                elif op=='resources':engine.replace_resources(req['bundle'])
                elif op=='tune':engine.tune(req['changes'])
                elif op=='inspect':
                    self.send(inspect_rig(engine.rig,engine.clips));return
                elif op=='cell':
                    from .contact import evaluate_cell
                    self.send(evaluate_cell(engine.state['body'],req['vertices'],req['surface'],req['dt'],req['settings']));return
                elif op=='limb':
                    from .procedural import limb_target
                    self.send(limb_target(req['request']));return
                else:raise ValueError('Unknown operation')
                self.send(dict(state=engine.snapshot(),hash=engine.state_hash(),events=engine.events[-12:],incidents=engine.incidents))
            except (ValueError,KeyError,TypeError,ArithmeticError) as exc:self.send(dict(error=str(exc),incidents=engine.incidents),400)
    server=HTTPServer(('127.0.0.1',port),Handler);server.engine=engine
    return server

def serve(port=8770,scenario=None):
    server=make_server(port,scenario);print(f'Engine inspector: http://127.0.0.1:{server.server_port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
