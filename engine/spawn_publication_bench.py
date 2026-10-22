"""Offline spawn publication sequence with explicit inputs and bank storage."""
import argparse
import copy
import hashlib
import json
import math
import struct
from pathlib import Path
from reference.skeleton_parent_transform import publish_spawn_pose, reset_animation_bank_parent


def _pose(values):
    if not isinstance(values,(list,tuple)) or len(values)!=8:
        raise ValueError('eight pose lanes required')
    if not all(type(x) in (int,float) and math.isfinite(x) for x in values):
        raise ValueError('finite pose lanes required')
    return struct.pack('<8f',*values)


def run(request):
    try:
        return _run(copy.deepcopy(request))
    except (KeyError,TypeError,IndexError,OverflowError,struct.error) as exc:
        raise ValueError(f'invalid spawn request: {exc}') from exc


def _run(request):
    if not isinstance(request,dict) or request.get('branch')!='supplied_spawn_publication':
        raise ValueError('explicit supplied_spawn_publication branch required')
    encoded=json.dumps(request,sort_keys=True,separators=(',',':'),allow_nan=False)
    frames=request['frames'];initial=request['banks']
    if not isinstance(frames,list) or not 1<=len(frames)<=256:
        raise ValueError('one to 256 frames required')
    if not isinstance(initial,dict) or len(initial)>16:raise ValueError('at most 16 banks required')
    banks={}
    for key,value in initial.items():
        if type(key) is not str or not key or len(key)>64:raise ValueError('bounded bank names required')
        records=value['records'];count=value['count'];word=value['reset_word']
        if not isinstance(records,list) or len(records)>512:raise ValueError('at most 512 records per bank')
        if type(count) is not int or not 0<=count<=len(records):raise ValueError('count must fit supplied records')
        if type(word) is not int or not 0<=word<=0xffffffff:raise ValueError('uint32 reset word required')
        banks[key]=dict(parent=_pose(value['parent']),default_pose=_pose(value['default_pose']),
                        records=[_pose(p) for p in records],count=count,reset_word=word)
    output=[]
    for index,frame in enumerate(frames):
        slots=frame['slots']
        if slots is not None:
            if not isinstance(slots,list) or len(slots)!=2:raise ValueError('two slots or null required')
            if any(s is not None and (type(s) is not str or s not in banks) for s in slots):
                raise ValueError('slot must identify supplied bank or be null')
        estimate=frame['reciprocal_estimate']
        if type(estimate) not in (int,float) or not math.isfinite(estimate) or estimate<=0:
            raise ValueError('explicit positive finite reciprocal estimate required')
        events=[]
        def entity(state):events.append('entity');return 'supplied_entity'
        def parent(state,phase):
            events.append('parent_'+phase)
            return frame['position_parent' if phase=='position' else 'rotation_parent']
        def publish(entity,matrix):events.append('publish_entity')
        def skeleton(entity):events.append('find_skeleton');return None if slots is None else {'slots':slots}
        def reset(key,pose):
            events.append('reset_'+key)
            reset_animation_bank_parent(banks[key],_pose(pose['parent_position']+pose['parent_rotation']),
                True,lambda:struct.pack('<8f',0,0,0,0,0,0,0,1))
        result=publish_spawn_pose(dict(position=frame['position'],rotation=frame['rotation']),
            get_entity=entity,read_parent=parent,reciprocal_sqrt=lambda _:estimate,
            publish_entity=publish,find_skeleton=skeleton,reset_parent=reset,
            matrix_template=frame.get('matrix_template'))
        output.append(dict(index=index,events=events,**result))
    def decode(bank):
        return dict(parent=list(struct.unpack('<8f',bank['parent'])),
            default_pose=list(struct.unpack('<8f',bank['default_pose'])),
            records=[list(struct.unpack('<8f',p)) for p in bank['records']],
            count=bank['count'],reset_word=bank['reset_word'])
    return dict(schema=1,evidence='reconstructed_spawn_math_with_supplied_observations',
        input_sha256=hashlib.sha256(encoded.encode()).hexdigest(),game_process=False,
        native_entity_setter=False,frames=output,banks={k:decode(v) for k,v in banks.items()},
        limits=['Parents and reciprocal estimates are explicit inputs.',
                'Entity publication is recorded, not executed against a native entity.',
                'Bank defaults assume recovered initialization; no TLS concurrency model.',
                'No live scheduling, physics teleport or original-game replay guarantee.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True);parser.add_argument('--output')
    args=parser.parse_args()
    try:result=run(json.loads(Path(args.request).read_text()))
    except ValueError as exc:parser.error(str(exc))
    text=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:Path(args.output).write_text(text)
    else:print(text,end='')

if __name__=='__main__':main()
