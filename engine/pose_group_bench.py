"""Offline inspection of recovered group partition and ordinary-group processing.

Evidence: CENTRAL_IMPULSE.md, Runnable group partition inspection.
Synthetic storage and record-only callback services are explicit; no live access.
"""
import argparse
import copy
import json
from pathlib import Path
from .pose_group_components import prepare_pose_group_destinations
from .pose_group_destinations import assign_pose_group_destinations
from .pose_group_eligibility import pose_group_eligible
from .pose_group_migration import migrate_pose_group
from .pose_group_process import process_pose_group
from .pose_group_finalize import finalize_pose_group
from .pose_group_removal import remove_pose_group
from .pose_body_membership import append_pose_body, remove_pose_body, remove_body_constraints


def inspect(document):
    ordinary=document.get('schema')=='pose-group-process-v1'
    if document.get('schema') not in ('pose-group-partition-v1','pose-group-process-v1'):
        raise ValueError('Unsupported schema')
    if document.get('provenance') not in ('authored_synthetic','caller_supplied_observation'):
        raise ValueError('Explicit provenance required')
    sequence='ordinary_group_process' if ordinary else 'reached_multi_body_partition'
    if document.get('sequence')!=sequence:
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
    other_special=token(data['other_special_group']) if ordinary else None
    if ordinary:
        if data['callback_policy']!='record_only':raise ValueError('Explicit callback policy required')
        if type(data['source_flag']) is not int or not 0<=data['source_flag']<=255:
            raise ValueError('Raw source flag required')
        if type(data['invalid_body_index']) is not int or not 0<=data['invalid_body_index']<=0xffffffff:
            raise ValueError('Explicit uint32 body sentinel required')
    acquired=[token(v) for v in data['available_groups']]
    groups={};events=[]
    def new_group(t):
        g=dict(token=t)
        if ordinary:g.update(index=0,flag_a0=0)
        for prefix in ('','link_','pose_'):
            g[prefix+'count']=0;g[prefix+'capacity']=capacity;g[prefix+'slots']=[0]*capacity
        groups[t]=g;return g
    source=new_group(source_token);new_group(special_token)
    if ordinary:source['flag_a0']=data['source_flag']
    bodies={}
    for i,b in enumerate(data['bodies']):
        t=token(b['token'])
        for field,maximum in [('flags16',65535),('flags8',255)]:
            if type(b[field]) is not int or not 0<=b[field]<=maximum:raise ValueError('Raw metadata flags required')
        if type(b['resolved_links_clear']) is not bool:raise ValueError('Explicit resolved link eligibility required')
        if ordinary and (type(b['kind8']) is not int or not 0<=b['kind8']<=255):
            raise ValueError('Raw kind byte required')
        bodies[t]=dict(token=t,index=i,group=source_token,flags16=b['flags16'],
            metadata=dict(flags8=b['flags8'],kind8=b.get('kind8',0)),first_vector=b['first_vector'],
            second_vector=b['second_vector'],resolved_links_clear=b['resolved_links_clear'])
    if not ordinary and len(bodies)<2:raise ValueError('Multi-body branch requires at least two bodies')
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
    context=dict(group410=special_token)
    if ordinary:
        context['group408']=other_special
        for name in ('groups418','groups428','tracked','pending_links'):
            context[name]=dict(count=0,capacity=capacity,slots=[0]*capacity)
        listing=context['groups428' if source['flag_a0'] else 'groups418']
        listing['slots'][0]=source_token;listing['count']=1
    def grow_context(array,n):
        if n>4096:raise ValueError('Authored storage bound exceeded')
        events.append(dict(operation='grow_context',capacity=n))
        array['slots'].extend([0]*max(0,n-len(array['slots'])))
        array['capacity']=n
    def acquire():
        if not pending:raise ValueError('Supplied group identities exhausted')
        t=pending.pop(0);g=new_group(t)
        if ordinary:
            listing=context['groups418'];g['index']=listing['count']
            if listing['count']==listing['capacity']:
                grow_context(listing,8 if not listing['capacity'] else listing['capacity']*2)
            listing['slots'][listing['count']]=t;listing['count']+=1
        events.append(dict(operation='acquire',group=t));return t
    def eligible(c,b):
        return pose_group_eligible(b['first_vector'],b['second_vector'],*data['thresholds'],
                                  links_clear=lambda:b['resolved_links_clear'])
    def grow(g,family,n):
        prefix={'bodies':'','links':'link_','poses':'pose_'}[family]
        if n>4096:raise ValueError('Authored storage bound exceeded')
        events.append(dict(operation='grow',group=g['token'],family=family,capacity=n))
        g[prefix+'slots'].extend([0]*max(0,n-len(g[prefix+'slots'])))
        g[prefix+'capacity']=n
    components=None;prepared=None;assigned=None;working=None;unused=None
    def prepare(c,g,d):
        nonlocal components,prepared
        components=prepare_pose_group_destinations(g,d['slots'],acquire_group=acquire)
        prepared=list(d['slots']);return components
    def migrate(g,d):
        nonlocal assigned,working
        assigned=list(d['slots']);working=d
        migrate_pose_group(g,d,groups=groups,bodies=bodies,links=links,poses=poses,grow=grow)
    retirement=[]
    if ordinary:
        def finalize(c,g):
            events.append(dict(operation='finalize'))
            return finalize_pose_group(c,g,groups=groups,bodies=bodies,links=links,
                virtual40=lambda b:events.append(dict(operation='body_virtual40_intent',body=b['token'])),
                grow=grow_context)
        def prune(g,t):
            remove_body_constraints(g,t,links=links,poses=poses,
                clear_link=lambda r:events.append(dict(operation='clear_link_intent',link=r['token'])))
        def allocate(n):
            events.append(dict(operation='allocate_temporary',bytes=n));return [0]*(n//8)
        def destroy(g,flags):
            retirement.append(dict(group=g['token'],flags=flags))
            events.append(dict(operation='destructor_intent',group=g['token'],flags=flags))
        retired=process_pose_group(context,source,bodies=bodies,finalize=finalize,
            eligible=eligible,
            remove_body=lambda g,b:remove_pose_body(g,b,bodies=bodies,remove_constraints=prune,
                                                   invalid_index=data['invalid_body_index']),
            append_body=lambda t,b:append_pose_body(groups[t],b,grow=lambda g,n:grow(g,'bodies',n)),
            allocate=allocate,prepare=prepare,acquire_group=lambda c:acquire(),migrate=migrate,
            release=lambda s:events.append(dict(operation='release_temporary')),
            remove_group=lambda c,g:remove_pose_group(c,g,groups=groups),destroy=destroy)
    else:
        working=dict(count=len(bodies),slots=[0]*len(bodies))
        prepare(context,source,working)
        unused=assign_pose_group_destinations(context,source,working['slots'],count=len(bodies),
            preparation_result=components,eligible=eligible,acquire_group=lambda c:acquire(),
            resolve_body=bodies.__getitem__)
        migrate(source,working)
    del source['links'];del source['poses']
    result=dict(schema=document['schema'],provenance=document['provenance'],
        component_count=components,prepared_destinations=prepared,assigned_destinations=assigned,
        remaining_destinations=working,original_group_reuse_available=unused,
        groups=groups,bodies=bodies,links=links,poses=poses,storage_events=events,
        limits=['Connected kernels validated offline with supplied storage services; JSON adapter is independently tested',
                'Resolved link eligibility supplied; native link acquisition and lifetime excluded',
                'List growth and supplied group identities are authored storage services',
                'No physics solve, live access or concurrency'])
    if ordinary:
        del result['original_group_reuse_available']
        result.update(context=context,retirement_requested=retired,destructor_intents=retirement)
        result['limits'].append('Full process composition is independently tested, not a continuous native execution receipt')
        result['limits'].append('Body virtual, link-clear and destructor calls are recorded intents only; effects are not executed')
        result['limits'].append('Retired group snapshots remain for inspection; they are not live objects or reusable handles')
    else:
        result['limits'].append('No outer finalization or destruction')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=inspect(json.loads(args.input.read_text()))
    encoded=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(encoded)
    else:print(encoded,end='')


if __name__=='__main__':main()
