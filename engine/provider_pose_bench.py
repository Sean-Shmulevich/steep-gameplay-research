"""Offline supplied-provider to procedural-pose sequence runner.

No collision backend, provider lookup, original-game access or skeleton commit.
RSQRT estimates are explicit input observations, not silently approximated.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from engine.pose_bench import run as run_tail
from reference.ground_response_pose import (entity_pose_transform,
    provider_pose_transform, pose_contact_axis, pose_adjustment_directions,
    resolved_pose_contact, pose_endpoint_origin, resolve_pose_channel)


def prepare(frame):
    frame=copy.deepcopy(frame)
    if 'provider_bank' in frame:
        if {'reference_provider','endpoint_providers'}.intersection(frame):
            raise ValueError('provider-bank results must not be overridden')
        bank=frame['provider_bank']
        frame['reference_provider']=resolve_pose_channel(bank,0x2c52cbb0)
        frame['endpoint_providers']=[resolve_pose_channel(bank,k) for k in (0x74cb19e4,0xaf72d919)]
    endpoint_origins=None
    if 'endpoint_records' in frame:
        records=frame['endpoint_records']
        if not isinstance(records,(list,tuple)) or len(records)!=2:
            raise ValueError('two endpoint records required')
        if {'origins','rotations'}.intersection(frame['tail']):
            raise ValueError('endpoint-record outputs must not be overridden')
        endpoint_origins=[pose_endpoint_origin(**r) for r in records]
        if len(frame['contacts'])!=2:raise ValueError('two contacts required')
        for contact,origin in zip(frame['contacts'],endpoint_origins):
            if {'endpoint','initial_point'}.intersection(contact):
                raise ValueError('endpoint-record contact origins must not be overridden')
            contact.update(endpoint=origin['origin'],initial_point=origin['origin'])
        frame['tail'].update(origins=[r['origin'] for r in endpoint_origins],
                             rotations=[r['rotation'] for r in endpoint_origins])
    entity=entity_pose_transform(**frame['entity_transform'])
    reference=provider_pose_transform(**frame['reference_provider'])
    axis=pose_contact_axis(reference['position'],entity['position_scalar'],frame['fallback_axis'])
    providers=frame['endpoint_providers'];observations=frame['contacts'];estimates=frame['rsqrt_estimates']
    if any(not isinstance(v,(list,tuple)) or len(v)!=2 for v in (providers,observations,estimates)):
        raise ValueError('two endpoint providers, contacts and estimate sequences required')
    endpoints=[]
    for provider,contact,seeds in zip(providers,observations,estimates):
        converted=provider_pose_transform(**provider)
        if not isinstance(seeds,(list,tuple)):raise ValueError('explicit estimate sequence required')
        seeds=iter(seeds)
        def estimate(n):
            try:return next(seeds)
            except StopIteration:raise ValueError('missing reciprocal-square-root estimate') from None
        directions=pose_adjustment_directions(converted['rotation'],axis['axis'],estimate)
        if list(seeds):raise ValueError('unused reciprocal-square-root estimates')
        result=resolved_pose_contact(axis=axis['axis'],above_direction=directions['above_direction'],**contact)
        endpoints.append({'provider':converted,'directions':directions,**result})
    tail=copy.deepcopy(frame['tail'])
    derived={'reference','axis','above_directions','below_directions','endpoints','contact_scalars','provider_rotation'}
    if derived.intersection(tail):raise ValueError('derived tail inputs must not be overridden')
    tail.update(reference=axis['reference_position'],axis=axis['axis'],
        above_directions=[e['above_direction'] for e in endpoints],
        below_directions=[e['directions']['below_direction'] for e in endpoints],
        endpoints=[e['contact']['point'] for e in endpoints],
        contact_scalars=[e['contact']['scalar'] for e in endpoints],
        provider_rotation=reference['rotation'])
    return tail,{'entity':entity,'reference_provider':reference,'axis':axis,'endpoints':endpoints,'endpoint_origins':endpoint_origins}


def run(request):
    if not isinstance(request,dict) or request.get('branch')!='supplied_provider_active_pose':
        raise ValueError('explicit supplied_provider_active_pose branch required')
    frames=request.get('frames')
    if not isinstance(frames,list) or not 1<=len(frames)<=2400:
        raise ValueError('one to 2400 provider frames required')
    encoded=json.dumps(request,sort_keys=True,separators=(',',':'),allow_nan=False)
    prepared=[];diagnostics=[]
    for i,frame in enumerate(frames):
        try:tail,detail=prepare(frame)
        except (KeyError,TypeError,IndexError,OverflowError,ValueError) as exc:
            raise ValueError(f'invalid provider frame {i}: {exc}') from exc
        prepared.append(tail);diagnostics.append(detail)
    result=run_tail({'branch':'resolved_active_tail','initial_state':request.get('initial_state'),'frames':prepared})
    result['resolved_tail_input_sha256']=result['input_sha256']
    result['input_sha256']=hashlib.sha256(encoded.encode()).hexdigest()
    result['evidence']='authored_composition_of_locally_recovered_math_with_supplied_provider_and_hit_records'
    result['branch']=request['branch'];result['collision_query_executed']=False
    result['supplied_channel_lookup']=any('provider_bank' in frame for frame in frames)
    result['rsqrt_estimates']='supplied; origin and hardware equivalence not verified by this runner'
    result['limits'] += ['Provider records and fallback transform are supplied, not acquired.',
        'Endpoint origins can be derived from supplied endpoint records; stored length and blend remain observations.',
        'Composition has not been validated as one uninterrupted original update.']
    for record,detail in zip(result['records'],diagnostics):record['preparation']=detail
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True);parser.add_argument('--output')
    args=parser.parse_args()
    try:result=run(json.loads(Path(args.request).read_text()));text=json.dumps(result,indent=2,allow_nan=False)+'\n'
    except (ValueError,OSError) as exc:parser.exit(2,f'{exc}\n')
    if args.output:Path(args.output).write_text(text)
    else:print(text,end='')


if __name__=='__main__':main()
