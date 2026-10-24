"""Offline JSON inspection of the recovered single-family link row builder.

Evidence: CENTRAL_IMPULSE.md, Runnable link-builder inspection.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import struct
from reference.central_impulse import f32
from .pose_link_builder import build_pose_link_rows


def inspect(document):
    if document.get('schema')!='pose-link-builder-v1':raise ValueError('Unsupported schema')
    if document.get('provenance') not in ('authored_synthetic','caller_supplied_observation'):
        raise ValueError('Explicit provenance required')
    if document.get('sequence')!='reached_metadata_clear_single':raise ValueError('Explicit reached builder required')
    data=copy.deepcopy(document['inputs'])
    def uint(value,bits):
        if type(value) is not int or not 0<=value<1<<bits:raise ValueError(f'Raw uint{bits} required')
        return value
    def scalar(value):
        if type(value) not in (int,float) or not math.isfinite(f32(value)):
            raise ValueError('Finite float32 number required')
    def vector(v):
        if len(v)!=3:raise ValueError('Three components required')
        for x in v:scalar(x)
    def decoded(value,size):
        result=bytearray.fromhex(value)
        if len(result)!=size:raise ValueError(f'Complete {size}-byte storage required')
        return result
    payload=decoded(data['payload_hex'],288)
    count=struct.unpack_from('<I',payload,0x110)[0]
    if count>4:raise ValueError('At most four payload rows required')
    context=data['context']
    for name in ('primary_count','secondary_count','result_count','flags38'):uint(context[name],32)
    for name in ('scalar_c','factor14','field1c','field20'):scalar(context[name])
    initial={name:context[name] for name in ('primary_count','secondary_count','result_count')}
    for name,size,needed,start in (('primary',112,count,initial['primary_count']),
                                   ('secondary',112,2*count,initial['secondary_count']),
                                   ('result',16,3*count,initial['result_count'])):
        raw=context.pop(name+'_rows_hex')
        if len(raw)>4096 or start+needed>len(raw):raise ValueError('Insufficient or oversized retained storage')
        context[name+'_rows']=[decoded(v,size) for v in raw]
    first,second=data['first_body'],data['second_body']
    for body in (first,second):
        uint(body['index1c'],16)
        frame=body['frame']
        if len(frame['basis'])!=3:raise ValueError('Three basis rows required')
        for row in frame['basis']:vector(row)
        vector(frame['translation'])
    for name in ('offset128','motion1a0','motion1ac'):vector(first[name])
    for resource in data['resources'].values():
        uint(resource['kind28'],16)
        for key in ('map60','mapb0'):
            if resource.get(key) is not None:
                if not isinstance(resource[key],list) or len(resource[key])>1048576:raise ValueError('Bounded byte map list required')
                for value in resource[key]:uint(value,8)
    for profile in data['profiles'].values():
        for value in profile.values():scalar(value)
    for mode in data['modes'].values():uint(mode,32)
    build_pose_link_rows(context,first,second,payload,resources=data['resources'],
                         profiles=data['profiles'],modes=data['modes'])
    def row_view(row):
        return dict(body_indices=list(struct.unpack_from('<HH',row)),
                    result_index=struct.unpack_from('<I',row,4)[0],
                    response=list(struct.unpack_from('<4f',row,0x10)),
                    direction=list(struct.unpack_from('<4f',row,0x20)),
                    angular_direction=list(struct.unpack_from('<4f',row,0x30)),
                    field50_words=list(struct.unpack_from('<2I',row,0x50)),
                    coefficient=list(struct.unpack_from('<4f',row,0x60)))
    output=dict(schema=document['schema'],provenance=document['provenance'],active_count=count,
                initial_counters=initial,final_counters={k:context[k] for k in initial},
                primary=[row_view(r) for r in context['primary_rows'][initial['primary_count']:context['primary_count']]],
                secondary=[row_view(r) for r in context['secondary_rows'][initial['secondary_count']:context['secondary_count']]],
                payload_hex=payload.hex(),
                limits=['Reached metadata-clear/single builder only; dispatcher admission is caller supplied',
                        'All prior storage bytes and resource/profile identities supplied; no allocation or live pointers',
                        'Result bytes show cache seeding only, not a solver iteration',
                        'Physical units, other builder families and native lifetime remain unresolved',
                        'JSON guards and inspection bounds are authored, not native failure behavior'])
    for name in ('primary','secondary','result'):
        output[name+'_rows_hex']=[r.hex() for r in context[name+'_rows']]
    json.dumps(output,allow_nan=False)
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    output=json.dumps(inspect(json.loads(args.input.read_text())),indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(output)
    else:print(output,end='')


if __name__=='__main__':main()
