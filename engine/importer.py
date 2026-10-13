"""Local-only adapter CLI. Writes user-selected private output, never source assets."""
import argparse
import json
from pathlib import Path
from .asset_adapter import from_decoded

def main():
    parser=argparse.ArgumentParser(description='Convert a local decoded pose-assembly export to an engine scenario')
    parser.add_argument('source');parser.add_argument('--rig',required=True);parser.add_argument('--clip',action='append',required=True);parser.add_argument('--unit-scale',required=True,type=float);parser.add_argument('--loop',action='store_true');parser.add_argument('--output',required=True)
    args=parser.parse_args();source=Path(args.source);destination=Path(args.output).resolve();repo=Path(__file__).resolve().parents[1]
    if destination.is_relative_to(repo):raise ValueError('Decoded asset output must stay outside the public source repository')
    data=json.loads(source.read_text());rig=data['skeletons'][args.rig];by_name={c['name']:c for c in data['representative_clips']}
    clips=[by_name[name] for name in args.clip]
    converted=from_decoded(rig,clips,unit_scale=args.unit_scale,looping={name:args.loop for name in args.clip})
    scenario={'schema_version':1,'sport':'snowboard','resources':converted['bundle']}
    destination.write_text(json.dumps(scenario,indent=2)+'\n')
    print(json.dumps({'written':str(destination),'rig':args.rig,'clips':len(clips),'diagnostics':converted['diagnostics']},indent=2))

if __name__=='__main__':main()
