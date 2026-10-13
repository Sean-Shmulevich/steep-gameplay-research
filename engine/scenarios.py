"""Repeatable sport stress runs with exact replay checks; synthetic world only."""
import argparse
import json
from pathlib import Path
from .runtime import Engine,SPORTS
from .replay import record,replay

def run(ticks=3600):
    if type(ticks) is not int or ticks<1:raise ValueError('Positive tick count required')
    results=[]
    for sport in SPORTS:
        e=Engine({'sport':sport,'world':{'slope':[-.2,.02],'bumps':[{'center':[20,0],'height':2,'radius':4}],'obstacles':[{'center':[35,3],'radius':.6,'height':6}]}})
        for start in range(0,ticks,120):
            i=start//120
            e.set_input({'steer':.4 if i%4<2 else -.3,'flip':.2 if i%3==0 else 0,'jump':i%6 in (1,2),'brake':i%10==9,'tuck':i%5==0})
            e.step(min(120,ticks-start))
        other=replay(record(e))
        results.append(dict(sport=sport,ticks=e.state['tick'],hash=e.state_hash(),replay_matches=e.state_hash()==other.state_hash(),incidents=len(e.incidents),events=len(e.events),score=e.state['scoring']['total']))
    return results

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ticks',type=int,default=3600);parser.add_argument('--output');args=parser.parse_args()
    results=run(args.ticks);output=json.dumps(results,indent=2)+'\n'
    if args.output:Path(args.output).write_text(output)
    print(output)
