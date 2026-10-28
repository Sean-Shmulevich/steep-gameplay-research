"""Offline persistent terrain contacts; LINK_SOLVER.md, Terrain-cache inspection CLI."""
import argparse
import copy
import json
from pathlib import Path
import struct
from .pose_grid_box_bench import prepare
from .pose_grid_box_contact import emit_grid_box_contacts,emit_box_grid_contacts
from .pose_contact_dispatch import process_dispatched_contact_pair


def inspect(document):
    if document.get('schema')!='pose-terrain-cache-v1':raise ValueError('Unsupported schema')
    provenance=document.get('provenance')
    if provenance not in ('authored_synthetic','caller_supplied_observation'):
        raise ValueError('Explicit provenance required')
    def integer(v,lo,hi):
        if type(v) is not int or not lo<=v<=hi:raise ValueError('Integer outside inspection bounds')
        return v
    def blob(value,size):
        result=bytearray.fromhex(value)
        if len(result)!=size:raise ValueError('Incorrect retained byte count')
        return result
    state=copy.deepcopy(document['initial_state'])
    payloads={int(key):blob(value,288) for key,value in state['payloads'].items()}
    for identity in payloads:integer(identity,1,2**64-1)
    owner=integer(state['owner'],0,2**64-1)
    cache=state['cache'];recycle=state['recycled']
    for collection in (cache,recycle):
        integer(collection['capacity'],0,256)
        integer(collection['count'],0,collection['capacity'])
        if len(collection['slots'])!=collection['capacity']:raise ValueError('Complete retained slots required')
    cache['slots']=[bytes(blob(v,16)) for v in cache['slots']]
    for identity in recycle['slots']:integer(identity,0,2**64-1)
    required=[struct.unpack_from('<Q',r,8)[0] for r in cache['slots'][:cache['count']]]+recycle['slots'][:recycle['count']]
    if any(identity not in payloads for identity in required):raise ValueError('Active identity lacks payload storage')
    output=blob(state['output_hex'],24000)
    pair=document['pair'];first,second=pair['indices'];flags=pair['flags']
    for i in (first,second):integer(i,0,65535)
    if len(flags)!=2:raise ValueError('Two entry flags required')
    for flag in flags:integer(flag,0,255)
    width=integer(pair['key_width'],16,32)
    if width not in (16,32):raise ValueError('Key width must be16 or32')
    reverse=pair['order']=='box_terrain'
    if pair['order'] not in ('terrain_box','box_terrain'):raise ValueError('Explicit pair order required')
    steps=document['steps']
    if not isinstance(steps,list) or not 1<=len(steps)<=64:raise ValueError('One to64 steps required')
    def supply(n):raise ValueError('Recycler exhausted; supply more initial payloads')
    def append(c,a,b,d,p):
        if c['count']==c['capacity']:raise ValueError('Cache capacity exhausted; supply more initial slots')
        c['slots'][c['count']]=struct.pack('<HHIQ',a,b,d,p);c['count']+=1
    results=[]
    for step in steps:
        geometry={'schema':'pose-grid-box-v1','provenance':provenance,'inputs':step}
        parsed=prepare(geometry,capacity_limit=500)
        if parsed['capacity']!=500:raise ValueError('Native handoff requires capacity500')
        terrain,box=parsed['frames'];ordered=(box,terrain) if reverse else (terrain,box)
        def generate(descriptor,buffer,capacity):
            function=emit_box_grid_contacts if reverse else emit_grid_box_contacts
            return function(buffer,capacity,parsed['resource'],parsed['samples'],*ordered,
                parsed['extents'],step['terrain_profiles'],step['box_profile'],
                profiles=step['profiles'],preliminary=step['preliminary'],
                edge_enabled=step['edge_enabled'],filter_enabled=step['filter_enabled'])
        kinds=(3,7) if reverse else (7,3);handlers=[None]*64;handlers[kinds[0]*8+kinds[1]]=generate
        frames=[dict(basis=f[:3],translation=f[3]) for f in ordered]
        result=process_dispatched_contact_pair(handlers,[{'kind':kinds[0]}]*(first+1),
            [{'kind':kinds[1]}]*(second+1),first,second,None,output,cache=cache,
            recycled=recycle,key_width=width,owner=owner,payloads=payloads,
            first_frame=frames[0],second_frame=frames[1],first_flags=flags[0],
            second_flags=flags[1],supply_batch=supply,append_entry=append)
        results.append({**result,'cache_count':cache['count'],'recycled_count':recycle['count'],
            'active_entries':[dict(zip(('first','second','detail','payload'),struct.unpack('<HHIQ',r))) for r in cache['slots'][:cache['count']]],
            'output_hex':output.hex(),'payloads':{str(k):v.hex() for k,v in payloads.items()}})
    final={'owner':owner,'cache':{**cache,'slots':[r.hex() for r in cache['slots']]},
           'recycled':recycle,'payloads':{str(k):v.hex() for k,v in payloads.items()},'output_hex':output.hex()}
    return {'schema':document['schema'],'provenance':provenance,'steps':results,'final_state':final,
        'limits':['Independent serial terrain/contact-cache inspection; no body integration or solver',
                  'Explicit initial payloads and storage; no native allocator, pool locking or game access',
                  'Input packing, diagnostics and snapshot format are authored; provenance is caller asserted']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=json.dumps(inspect(json.loads(args.input.read_text())),indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(result)
    else:print(result,end='')


if __name__=='__main__':main()
