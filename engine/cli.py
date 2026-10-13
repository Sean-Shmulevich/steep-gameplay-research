"""Headless run/replay/server entrypoint. No original game required."""
import argparse
import json
from pathlib import Path
from .runtime import Engine,SPORTS
from .replay import record,replay

def main():
    p=argparse.ArgumentParser();p.add_argument('--scenario');p.add_argument('--sport',choices=SPORTS,default='snowboard');p.add_argument('--ticks',type=int,default=600);p.add_argument('--output');p.add_argument('--replay');p.add_argument('--serve',action='store_true');p.add_argument('--port',type=int,default=8770)
    args=p.parse_args()
    if args.serve:
        from .server import serve
        serve(args.port,json.loads(Path(args.scenario).read_text()) if args.scenario else None);return
    if args.replay:engine=replay(json.loads(Path(args.replay).read_text()))
    else:
        scenario=json.loads(Path(args.scenario).read_text()) if args.scenario else {'sport':args.sport}
        engine=Engine(scenario);engine.step(args.ticks)
    if args.output:Path(args.output).write_text(json.dumps(record(engine),indent=2)+'\n')
    print(json.dumps(dict(tick=engine.state['tick'],hash=engine.state_hash(),body=engine.state['body'],score=engine.state['scoring'],incidents=engine.incidents),indent=2))

if __name__=='__main__':main()
