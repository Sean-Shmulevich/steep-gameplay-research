"""Offline JSON evaluator for recovered selector-2 pose-bank operations.

Requires explicit recorded or authored normalization policy. No game access.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from reference.animation_channels import evaluate_numeric_pose_bank, evaluate_grouped_pose_bank
from reference.central_impulse import f32



def evaluate_regular_bytes(inputs, seed, *, masked=False):
    """Authored JSON boundary around the recovered regular byte-bank evaluator."""
    from reference.animation_bank_blend import blend_regular_pose_bank, blend_masked_pose_bank
    values=deepcopy(inputs)
    for name in ('destination','first','second'):
        bank=values[name];data=bank['data']
        if not isinstance(data,list) or len(data)>1048576 or any(
                type(v) is not int or not 0<=v<=255 for v in data):
            raise ValueError('bank data must contain at most 1 MiB of integer bytes')
        bank['data']=bytearray(data)
        profile=bank['profile']
        if len(profile['descriptors'])>4096:raise ValueError('at most 4096 descriptors')
        for descriptor in profile['descriptors']:
            if any(type(descriptor[k]) is not int or not 0<=descriptor[k]<=65535
                   for k in ('kind','offset')):
                raise ValueError('uint16 descriptor offset/type required')
            if masked and (type(descriptor.get('key')) is not int or not 0<=descriptor['key']<=0xffffffff):
                raise ValueError('masked descriptors require uint32 keys')
        if len(bank['records'])>255:raise ValueError('at most 255 supplemental records')
    for key,limit in (('selector',7),('request_mask',65535),('exclusion_mask',0xffffffff)):
        value=values.get(key,0)
        if type(value) is not int or not 0<=value<=limit:raise ValueError(key+' outside range')
    flags=values['destination']['flags']
    if type(flags) is not int or not 0<=flags<=0xffffffff:raise ValueError('uint32 flags required')
    if masked:
        for key,limit in (('weight_mode',1),('uniform_groups',65535)):
            value=values.get(key,1 if key=='weight_mode' else 0)
            if type(value) is not int or not 0<=value<=limit:
                raise ValueError(key+' outside range')
    evaluator=blend_masked_pose_bank if masked else blend_regular_pose_bank
    visits=evaluator(**values,reciprocal_sqrt=seed)
    destination=values['destination']
    return dict(data=list(destination['data']),flags=destination['flags'],
                records=destination['records'],ranges=visits)


def run(document):
    if document.get('schema') != 'animation-bank-bench-v1':
        raise ValueError('animation-bank-bench-v1 schema required')
    cases=document.get('cases')
    if not isinstance(cases,list) or not 1<=len(cases)<=64:
        raise ValueError('provide 1..64 cases')
    results=[]
    for case in cases:
        policy=case.get('seed_policy')
        if policy not in ('recorded','authored_exact_sqrt'):
            raise ValueError('explicit recorded or authored_exact_sqrt policy required')
        observations=case.get('normalization',[])
        if not isinstance(observations,list):raise ValueError('normalization observations must be a list')
        if policy=='authored_exact_sqrt' and observations:
            raise ValueError('authored policy must not consume recorded observations')
        trace=[]
        def seed(length):
            if policy=='recorded':
                if len(trace)>=len(observations):raise ValueError('missing normalization observation')
                observed=observations[len(trace)]
                if length!=f32(observed['length']):raise ValueError('normalization input differs from recording')
                estimate=f32(observed['seed'])
                if not math.isfinite(estimate) or estimate<=0:raise ValueError('positive finite seed required')
            else:
                estimate=f32(1/math.sqrt(length))
            trace.append(dict(length=length,seed=estimate))
            return estimate
        inputs=case['inputs']
        if len(inputs.get('kinds',[]))>4096:raise ValueError('at most 4096 channels per case')
        entry=case.get('entry','inner')
        if entry not in ('inner','group_wrapper','regular_bytes','masked_bytes'):raise ValueError('unknown bank entry')
        evaluator=evaluate_grouped_pose_bank if entry=='group_wrapper' else evaluate_numeric_pose_bank
        result=(evaluate_regular_bytes(inputs,seed,masked=entry=='masked_bytes') if entry in ('regular_bytes','masked_bytes')
                else evaluator(**inputs,reciprocal_sqrt=seed))
        if policy=='recorded' and len(trace)!=len(observations):
            raise ValueError('unused normalization observations')
        results.append(dict(label=case.get('label',''),entry=entry,seed_policy=policy,
                            normalization=trace,result=result))
    encoded=json.dumps(document,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return dict(schema='animation-bank-bench-result-v1',input_sha256=hashlib.sha256(encoded).hexdigest(),
        evidence='offline supplied-input reconstruction; not a game capture or full engine equivalence',
        domain='inner/group_wrapper: selector 2 modes 0/4 kinds 1/5/6; regular_bytes/masked_bytes: mode-zero bank routers with separate byte banks',cases=results)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        result=run(json.loads(args.input.read_text()))
        text=json.dumps(result,indent=2,allow_nan=False)+'\n'
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        parser.error(str(exc))
    if args.output:args.output.write_text(text)
    else:print(text,end='')


if __name__=='__main__':main()
