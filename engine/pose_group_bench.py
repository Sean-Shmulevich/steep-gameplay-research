"""Offline inspection of recovered component preparation through group migration.

Evidence: CENTRAL_IMPULSE.md, Runnable group partition inspection.
Synthetic storage services are explicit; no native object access or destruction.
"""
import argparse
import copy
import json
from pathlib import Path
from .pose_group_components import prepare_pose_group_destinations
from .pose_group_destinations import assign_pose_group_destinations
from .pose_group_eligibility import pose_group_eligible
from .pose_group_migration import migrate_pose_group


def inspect(document):
    if document.get('schema')!='pose-group-partition-v1':raise ValueError('Unsupported schema')
    if document.get('provenance') not in ('authored_synthetic','caller_supplied_observation'):
        raise ValueError('Explicit provenance required')
    if document.get('sequence')!='reached_multi_body_partition':
        raise ValueError('Explicit reached-branch assertion required')
    data=copy.deepcopy(document['inputs'])
    if data['storage_policy']!='authored_list_growth':raise ValueError('Explicit storage policy required')
    capacity=data['initial_capacity']
    if type(capacity) is not int or not 1<=capacity<=4096:raise ValueError('Capacity must be 1..4096')
    used=set()
    def token(value):
        if type(value) is not int or not 0<value<=0xffffffffffffffff or value in used:
            raise ValueError('Unique nonzero uint64 tokens required')
        used.add(value);return value
    source_token=token(data['source_group']);special_token=token(data['special_group'])
    acquired=[token(v) for v in data['available_groups']]
    groups={};events=[]
    def new_group(t):
        g=dict(token=t)
        for prefix in ('','link_','pose_'):
            g[prefix+'count']=0;g[prefix+'capacity']=capacity;g[prefix+'slots']=[0]*capacity
        groups[t]=g;return g
    source=new_group(source_token);new_group(special_token)
    bodies={}
    for i,b in enumerate(data['bodies']):
        t=token(b['token'])
        for field,maximum in [('flags16',65535),('flags8',255)]:
            if type(b[field]) is not int or not 0<=b[field]<=maximum:raise ValueError('Raw metadata flags required')
        if type(b['resolved_links_clear']) is not bool:raise ValueError('Explicit resolved link eligibility required')
        bodies[t]=dict(token=t,index=i,group=source_token,flags16=b['flags16'],
            metadata=dict(flags8=b['flags8']),first_vector=b['first_vector'],
            second_vector=b['second_vector'],resolved_links_clear=b['resolved_links_clear'])
    if len(bodies)<2:raise ValueError('Multi-body branch requires at least two bodies')
    links={};poses={}
    for name,records in [('links',links),('poses',poses)]:
        for i,r in enumerate(data[name]):
            t=token(r['token']);first=r['first'];second=r['second']
            if first not in bodies or (second not in bodies and not (name=='poses' and second is None)):
                raise ValueError('Retained endpoints required')
            records[t]=dict(token=t,index=i,first=first,second=second)
            if name=='poses':records[t]['group']=source_token
    for prefix,records in [('',bodies),('link_',links),('pose_',poses)]:
        if len(records)>capacity:raise ValueError('Initial capacity smaller than source records')
        source[prefix+'count']=len(records);source[prefix+'slots'][:len(records)]=list(records)
    source['links']=[(bodies[r['first']],bodies[r['second']]) for r in links.values()]
    source['poses']=[(bodies[r['first']],None if r['second'] is None else bodies[r['second']]) for r in poses.values()]
    pending=list(acquired)
    def acquire():
        if not pending:raise ValueError('Supplied group identities exhausted')
        t=pending.pop(0);new_group(t);events.append(dict(operation='acquire',group=t));return t
    destinations=[0]*len(bodies)
    components=prepare_pose_group_destinations(source,destinations,acquire_group=acquire)
    prepared=list(destinations)
    # Destination completion reads body objects, while migration stores tokens.
    selection=dict(token=source_token,slots=[bodies[t] for t in source['slots'][:source['count']]])
    context=dict(group410=special_token)
    def eligible(c,b):
        return pose_group_eligible(b['first_vector'],b['second_vector'],*data['thresholds'],
                                  links_clear=lambda:b['resolved_links_clear'])
    unused=assign_pose_group_destinations(context,selection,destinations,count=len(bodies),
        preparation_result=components,eligible=eligible,acquire_group=lambda c:acquire())
    assigned=list(destinations)
    def grow(g,family,n):
        prefix={'bodies':'','links':'link_','poses':'pose_'}[family]
        if n>4096:raise ValueError('Authored storage bound exceeded')
        events.append(dict(operation='grow',group=g['token'],family=family,capacity=n))
        g[prefix+'slots'].extend([0]*max(0,n-len(g[prefix+'slots'])))
        g[prefix+'capacity']=n
    working=dict(count=len(bodies),slots=destinations)
    migrate_pose_group(source,working,groups=groups,bodies=bodies,links=links,poses=poses,grow=grow)
    del source['links'];del source['poses']
    return dict(schema=document['schema'],provenance=document['provenance'],
        component_count=components,prepared_destinations=prepared,assigned_destinations=assigned,
        remaining_destinations=working,original_group_reuse_available=unused,
        groups=groups,bodies=bodies,links=links,poses=poses,storage_events=events,
        limits=['Connected kernels validated offline with supplied storage services; JSON adapter is independently tested',
                'Resolved link eligibility supplied; native link acquisition and lifetime excluded',
                'List growth and supplied group identities are authored storage services',
                'No outer finalization, destruction, physics solve, live access or concurrency'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=inspect(json.loads(args.input.read_text()))
    encoded=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(encoded)
    else:print(encoded,end='')


if __name__=='__main__':main()
