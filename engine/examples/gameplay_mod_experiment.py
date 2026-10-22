"""Record controls, speed mods, recovered animation arithmetic and physics together.

Uses the independent controller with synthetic resources and authored graph
selection. No game process, extracted assets or original replay fidelity claim.
"""
import argparse
import json
from pathlib import Path
from engine.control import SchedulerController
from engine.replay import replay


def run(*, physics_mode='point', sport='snowboard'):
    if physics_mode not in ('point','rigid_cells') or sport not in ('snowboard','ski'):
        raise ValueError('Expected point/rigid_cells and snowboard/ski')
    scenario=json.loads(Path(__file__).with_name('byte_pose_graph.json').read_text())
    scenario.update(execution_mode='mixed', physics_mode=physics_mode, sport=sport, trace={'capacity':50000},
                    scheduler={'mode':'subdivision'}, body={'velocity':[10,0,0]})
    nodes=scenario['animation']['graph']['nodes']
    nodes['mix']['weight']={'input':'jump'}
    nodes['layer']['weight']={'input':'lean'}
    controller=SchedulerController(scenario)
    token=controller.pause()
    samples=[]
    def sample(label):
        snapshot=controller.snapshot(include_trace=False);state=snapshot['state']
        samples.append(dict(label=label,tick=state['tick'],time=state['time'],
                            input_generation=state['input_generation'],controls=state['controls'],
                            body=state['body'],local_pose=state['pose']['local_pose'],
                            animation=state['pose']['diagnostics'],
                            physics=state['diagnostics'].get('physics',{})))
    sample('initial')
    token=controller.adjust_speed(token,2);sample('boost')
    for label,frames,actions in (
        ('approach',18,{'steer':.4,'lean':.5}),
        ('charge',24,{'jump':True,'lean':.2}),
        ('release',30,{'steer':-.3,'flip':.4,'lean':-.3}),
        ('settle',120,{}),
        ('brake_input',30,{'brake':True})):
        for frame in range(frames):
            # Unequal outer-frame intervals exercise scheduler subdivision.
            controller.step_frame_once(token,(1/60 if frame%2==0 else 1/50),actions,include_trace=False)
            sample(label)
    token=controller.adjust_speed(token,-2);sample('brake_mod')
    checkpoint=controller.checkpoint()
    recording=controller.export_replay()
    restored=replay(recording)
    equal=restored.snapshot()==controller.snapshot()['state']
    events_equal=restored.events==checkpoint['engine']['events']
    pulses=[c for c in recording['commands'] if c['op']=='adjust_speed']
    return dict(schema_version=1,physics_mode=physics_mode,sport=sport,
                scope='independent engine integration; synthetic clips and authored selection',
                replay_equal=equal,events_equal=events_equal,speed_commands=pulses,
                samples=samples,events=checkpoint['engine']['events'],
                incidents=checkpoint['incidents'],trace=controller.snapshot()['trace'],
                replay=recording)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--physics-mode',choices=('point','rigid_cells'),default='point')
    parser.add_argument('--sport',choices=('snowboard','ski'),default='snowboard')
    args=parser.parse_args()
    report=run(physics_mode=args.physics_mode,sport=args.sport)
    Path(args.output).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    summary={k:report[k] for k in ('replay_equal','events_equal','incidents')}
    summary.update(samples=len(report['samples']),final_tick=report['samples'][-1]['tick'],
                   trace_complete=report['trace']['complete'])
    print(json.dumps(summary))
    if not all((report['replay_equal'],report['events_equal'],report['trace']['complete'])) or report['incidents']:
        raise SystemExit(1)


if __name__=='__main__':main()
