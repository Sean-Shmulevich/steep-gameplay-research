"""Runnable contact build/solve/correction inspector; LINK_SOLVER.md, Contact inspector."""
import argparse
import copy
import json
from pathlib import Path
import struct
from .pose_link_counts import count_pose_link_rows
from .pose_solver_layout import plan_pose_solver_layout,initialize_pose_solver_storage
from .pose_link_arena import run_pose_contact_pass_from_bodies,correct_pose_contact_transforms,POOLS
from .pose_scalar_trig import scalar_sin_cos


def inspect(document):
    if document.get('schema')!='pose-contact-pass-v1':raise ValueError('Unsupported schema')
    if document.get('provenance') not in ('authored_synthetic','caller_supplied_observation'):
        raise ValueError('Explicit provenance required')
    d=copy.deepcopy(document['inputs']);order=d['body_order'];tokens=d['link_order']
    if not 1<=len(order)<=64 or len(set(order))!=len(order) or len(tokens)>128:
        raise ValueError('Bounded unique body order and link order required')
    flags=d['context']['flags38']
    if type(flags) is not int or not 0<=flags<=0xffffffff:raise ValueError('Raw context flags required')
    if ((flags>>2)&0x3fff)>64 or ((flags>>16)&0x7ff)>64:raise ValueError('Inspector iteration limit64 exceeded')
    raw={};bodies={}
    def xyz(b,offset):return list(struct.unpack_from('<3f',b,offset))
    def body_view(b):return dict(frame=dict(basis=[xyz(b,o) for o in (0x40,0x50,0x60)],translation=xyz(b,0x70)),
                                motion1a0=xyz(b,0x1a0),motion1ac=xyz(b,0x1ac))
    for index,token in enumerate(order):
        spec=d['bodies'][token];b=bytearray.fromhex(spec['raw_hex'])
        if not 0x1c0<=len(b)<=4096:raise ValueError('Complete bounded body storage required')
        if struct.unpack_from('<H',b,0x1c)[0]!=index:raise ValueError('Raw body index must match order')
        if struct.unpack_from('<Q',b,0x1b8)[0]:raise ValueError('Inspector does not supply damping response')
        raw[token]=b
        bodies[token]=dict(body_view(b),index1c=index,entries=spec['entries'],offset128=xyz(b,0x128),
            tensor170=[xyz(b,o) for o in (0x170,0x180,0x190)],scalar124=struct.unpack_from('<f',b,0x124)[0],
            flagsaa=b[0xaa],metadata_flags50=spec['metadata_flags50'],metadata_flags52=spec['metadata_flags52'],damping1b8=None)
    payloads={token:bytearray.fromhex(value) for token,value in d['payloads_hex'].items()}
    if len(payloads)>512 or any(len(p)!=288 or struct.unpack_from('<I',p,0x110)[0]>4 for p in payloads.values()):
        raise ValueError('Bounded complete payloads required')
    links=d['links']
    for token in tokens:
        link=links[token]
        if not 0<=link['payload_count']<=len(link['payload_slots'])<=512:raise ValueError('Bounded payload slots required')
    if sum(links[t]['payload_count'] for t in tokens)>4096:raise ValueError('Inspector payload visit limit exceeded')
    counts=[0]*25
    count_pose_link_rows(counts,tokens,links=links,bodies=bodies,payloads=payloads,mode=flags&3)
    plan=plan_pose_solver_layout(counts,len(order));arena=bytearray(plan['size'])
    initialize_pose_solver_storage(arena,counts,len(order));struct.pack_into('<I',arena,0x38,flags)
    for name,offset in (('scalar_c',0xc),('factor14',0x14),('field18',0x18),('field1c',0x1c),('field20',0x20)):
        struct.pack_into('<f',arena,offset,d['context'][name])
    before={t:body_view(b) for t,b in raw.items()}
    common=dict(links=links,bodies=bodies,payloads=payloads)
    run_pose_contact_pass_from_bodies(arena,tokens,**common,resources=d['resources'],profiles=d['profiles'],modes=d['modes'],
        body_tokens=order,raw_bodies=raw,scalar=d['body_scalar'],vector=d['external_vector'])
    first_pass={t:body_view(b) for t,b in raw.items()}
    view=memoryview(arena)
    data=[view[plan['body_data_offset']+64*i:plan['body_data_offset']+64*(i+1)] for i in range(len(order))]
    state=[view[plan['body_state_offset']+32*i:plan['body_state_offset']+32*(i+1)] for i in range(len(order))]
    corrected=correct_pose_contact_transforms(arena,tokens,**common,body_data=data,body_state=state,
        body_tokens=order,raw_bodies=raw,half_angle_trig=scalar_sin_cos)
    pools={name:[bytes(view[plan['rows_offset']+16*plan['category_starts'][category]+i*stride:
                           plan['rows_offset']+16*plan['category_starts'][category]+(i+1)*stride]).hex()
                 for i in range(counts[category])] for name,category,stride in POOLS}
    output=dict(schema=document['schema'],provenance=document['provenance'],planned_counts=counts,
        before=before,first_pass=first_pass,after={t:body_view(b) for t,b in raw.items()},secondary_ran=corrected,
        row_pools_hex=pools,payloads_hex={t:p.hex() for t,p in payloads.items()},raw_bodies_hex={t:b.hex() for t,b in raw.items()},
        result_rows_hex=[bytes(view[plan['results_offset']+16*i:plan['results_offset']+16*(i+1)]).hex() for i in range(sum(counts))],
        limits=['Authored JSON adapter and bounds; zero-initialized allocated arena',
                'Supplied contact payloads and body membership; no terrain contact generation',
                'No damping, pose constraints, group poststep or full simulation tick',
                'Constructor-selected transform update and dispatch-zero trig below500000 only'])
    json.dumps(output,allow_nan=False)
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=json.dumps(inspect(json.loads(args.input.read_text())),indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(result)
    else:print(result,end='')


if __name__=='__main__':main()
