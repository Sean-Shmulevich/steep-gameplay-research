"""Scripted headless scheduler experiments with explicit simulated durations.

No wall timers, OS input or original-process control. Commands are consumed in
stored order. Input is committed before the next explicit frame/step command.
Reports preserve per-frame plans, exact replay checks and trace loss status.
"""
import argparse
import copy
import json
from pathlib import Path
from .runtime import Engine
from .replay import record,replay
from .assets import canonical


def run(spec):
    canonical(spec)
    if spec.get('schema_version')!=1 or set(spec)-{'schema_version','scenario','commands'}:
        raise ValueError('Expected version-1 experiment')
    commands=spec.get('commands')
    if not isinstance(commands,list) or len(commands)>10000:raise ValueError('Invalid experiment commands')
    engine=Engine(spec.get('scenario',{}));checkpoints={};frames=[];checks=[]
    for index,command in enumerate(commands):
        op=command.get('op')
        if op=='input':engine.set_input(command['actions'])
        elif op=='advance':
            count=command.get('repeat',1)
            if type(count) is not int or not 1<=count<=10000:raise ValueError('Invalid frame repeat count')
            for _ in range(count):
                before=engine.state['tick'];engine.advance(command['dt'])
                frames.append(dict(command=index,start_tick=before,end_tick=engine.state['tick'],scheduler=copy.deepcopy(engine.state['scheduler'])))
        elif op=='step':engine.step(command.get('count',1))
        elif op=='checkpoint':checkpoints[command['name']]=engine.checkpoint()
        elif op=='restore':engine.restore(checkpoints[command['name']])
        elif op=='pause':engine.pause(command.get('value',True))
        elif op=='assert':
            path=command['path'];value=engine.snapshot()
            if not isinstance(path,list) or not path:raise ValueError('Assertion path must be a nonempty key list')
            for key in path:value=value[key]
            expected=command['equals'];passed=value==expected
            checks.append(dict(command=index,path=path,expected=expected,actual=value,passed=passed))
            if not passed:raise AssertionError(f'Experiment assertion failed at command {index}: {path}')
        else:raise ValueError('Unknown experiment operation')
    journal=record(engine);other=replay(journal)
    return dict(schema_version=1,scope='owned reconstruction only',state=engine.snapshot(),state_hash=engine.state_hash(),
                replay_equal=other.state_hash()==engine.state_hash(),frames=frames,checks=checks,
                trace=engine.trace.snapshot(),incidents=copy.deepcopy(engine.incidents),replay=journal)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec');parser.add_argument('--output',required=True)
    args=parser.parse_args();result=run(json.loads(Path(args.spec).read_text()))
    Path(args.output).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(replay_equal=result['replay_equal'],ticks=result['state']['tick'],frames=len(result['frames']),trace_complete=result['trace']['complete'],dropped=result['trace']['dropped'])))

if __name__=='__main__':main()
