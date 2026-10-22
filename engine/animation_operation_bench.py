"""Offline ordinary pose-operation evaluator. No game process or assets required."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from reference.animation_channels import evaluate_ordinary_pose_operation, evaluate_special_pose_operation
from reference.central_impulse import f32


def run(document):
    encoded=json.dumps(document,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if document.get('schema')!='animation-operation-bench-v1':
        raise ValueError('animation-operation-bench-v1 schema required')
    cases=document.get('cases')
    if not isinstance(cases,list) or not 1<=len(cases)<=64:raise ValueError('provide 1..64 cases')
    outputs=[]
    for case in cases:
        policy=case.get('math_policy')
        if policy not in ('recorded','authored_host_math'):
            raise ValueError('explicit recorded or authored_host_math policy required')
        services=case.get('services',[]);seeds=case.get('normalizations',[])
        if not isinstance(services,list) or not isinstance(seeds,list):
            raise ValueError('math recordings must be lists')
        if policy=='authored_host_math' and (services or seeds):
            raise ValueError('authored policy cannot consume recordings')
        inputs=case['inputs']
        entry=case.get('entry','ordinary')
        if entry not in ('ordinary','special'):raise ValueError('ordinary or special entry required')
        channels=inputs['kinds'] if entry=='ordinary' else inputs['descriptors']
        if not 1<=len(inputs['banks'])<=64 or len(channels)>4096:
            raise ValueError('at most 64 banks and 4096 channels required')
        if len(inputs['entry_masks'])>65535:raise ValueError('manager entry limit exceeded')
        for bank in inputs['banks'].values():
            if len(bank['channels'])!=len(channels) or len(bank['records'])>255:
                raise ValueError('matching channel count and at most 255 supplemental records required')
        trace=[];normalization=[]
        def service(name):
            def call(value):
                if policy=='recorded':
                    if len(trace)>=len(services):raise ValueError('missing math observation')
                    event=services[len(trace)]
                    if event['service']!=name or f32(event['input'])!=value:
                        raise ValueError('math observation does not match call')
                    result=f32(event['output'])
                else:result=f32((math.acos if name=='arccos' else math.sin)(value))
                if not math.isfinite(result):raise ValueError('finite math result required')
                trace.append(dict(service=name,input=value,output=result))
                return result
            return call
        def seed(length):
            if policy=='recorded':
                if len(normalization)>=len(seeds):raise ValueError('missing normalization observation')
                event=seeds[len(normalization)]
                if f32(event['length'])!=length:raise ValueError('normalization observation does not match call')
                result=f32(event['seed'])
            else:result=f32(1/math.sqrt(length))
            if not math.isfinite(result) or result<=0:raise ValueError('positive finite normalization seed required')
            normalization.append(dict(length=length,seed=result))
            return result
        evaluator=evaluate_ordinary_pose_operation if entry=='ordinary' else evaluate_special_pose_operation
        result=evaluator(**inputs,arccos=service('arccos'),
                                                sine=service('sine'),reciprocal_sqrt=seed)
        if policy=='recorded' and (len(trace)!=len(services) or len(normalization)!=len(seeds)):
            raise ValueError('unused math or normalization observations')
        outputs.append(dict(label=case.get('label',''),entry=entry,math_policy=policy,services=trace,
                            normalizations=normalization,result=result))
    return dict(schema='animation-operation-bench-result-v1',input_sha256=hashlib.sha256(encoded).hexdigest(),
        evidence='offline supplied-input reconstruction; lookup results supplied; no game capture',
        limitations=['special tangent producer and units unresolved','destination aliases unsupported',
                     'host math does not establish original numerical equivalence',
                     'no live scheduling or native storage ownership'],cases=outputs)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        result=run(json.loads(args.input.read_text()))
        text=json.dumps(result,indent=2,allow_nan=False)+'\n'
    except (ValueError,TypeError,KeyError,OverflowError,NotImplementedError) as exc:
        parser.error(str(exc))
    if args.output:args.output.write_text(text)
    else:print(text,end='')


if __name__=='__main__':main()
