#!/usr/bin/env python3
"""Recompute provider conversion from a private capture; emit aggregate checks only.

Checks internal consistency with the recovered formula, not an independent
observation of the game's provider-accessor output or coordinate semantics.
"""
import argparse
import json
import math
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reference.ground_response_pose import provider_pose_transform


def validate_conversion(capture):
    checked=0;matched=0;direct_count=0;composed_count=0;errors=[];skipped=0
    for index,row in enumerate(capture['rows']):
        response=row.get('animation',{})
        p=response.get('result',{})
        if response.get('status')!='completed' or not p.get('found'):
            skipped+=1;continue
        checked+=1
        try:
            flags=p['bank_flags'];direct=p['conversion_direct']
            if type(flags) is not int or not 0<=flags<=0xffffffff or type(direct) is not bool:
                raise ValueError('invalid flags')
            if direct!=bool(flags&(1<<26)):raise ValueError('branch disagrees with flags')
            record=p['record_index']
            if type(record) is not int or not 0<=record<65535:raise ValueError('invalid found record index')
            for name in ('vector','rotation','parent_vector','parent_rotation','provider_vector','provider_rotation'):
                value=p[name]
                if len(value)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) for x in value):
                    raise ValueError('invalid four-lane field')
            expected=provider_pose_transform(p['vector'],p['rotation'],p['parent_vector'],p['parent_rotation'],direct)
            direct_count+=int(direct)
            composed_count+=int(not direct)
            # Nine significant JSON digits preserve float32. Compare bytes after decoding.
            for name,target in [('provider_vector','position'),('provider_rotation','rotation')]:
                if struct.pack('<4f',*p[name])!=struct.pack('<4f',*expected[target]):
                    raise ValueError('float32 conversion mismatch')
            matched+=1
        except (KeyError,TypeError,ValueError,OverflowError,struct.error) as exc:
            errors.append({'row':index,'error':str(exc)})
    return dict(schema='provider-conversion-capture-check-v1',checked=checked,matched=matched,
                skipped=skipped,direct_branch=direct_count,composed_branch=composed_count,
                errors=errors,ok=checked>0 and matched==checked,
                original_accessor_independently_observed=False,coordinate_semantics_established=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path,help='Capture JSON, or host-session result containing animation')
    args=parser.parse_args()
    data=json.loads(args.capture.read_text())
    if 'probe' in data:data=data['probe']
    if 'animation' in data:data=data['animation']
    result=validate_conversion(data)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['ok'] else 1)
