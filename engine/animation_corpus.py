"""Payload-free diagnostics for caller-supplied serialized track boundaries."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from .animation_decoder import unpack_serialized_channel, registered_channel_decoder
from .animation_sampling import Channel, Resource, SampleState, sample_channel

SUPPORTED = frozenset((0,9,10,11,12,13,14,15,16,17,21,22,23,24,25,26,27,28,29,39,40,41,54,66))


def inspect_clip(body, records):
    """Exercise supported records; never include samples or names in the report.

    Records use codec, serialized_start/end, optional shared_track_reference.
    Boundaries are caller evidence, not discovered container offsets. Sampling
    checks independent repeatability with fresh versus retained cursors, not
    agreement with native output. Unsupported records are reported, not decoded.
    """
    counts=Counter();passed=0;samples=0;shared=0;failures=[]
    for index,record in enumerate(records):
        if 'shared_track_reference' in record:
            shared+=1
            continue
        codec=record.get('codec')
        if type(codec) is not int or not 0<=codec<=255:
            failures.append({'record':index,'reason':'invalid_codec'})
            continue
        counts[codec]+=1
        if codec not in SUPPORTED:
            continue
        try:
            start,end=record['serialized_start'],record['serialized_end']
            if type(start) is not int or type(end) is not int or not 0<=start<end<=len(body):
                raise ValueError('bounds')
            parsed=unpack_serialized_channel(body[start:end])
            if parsed['consumed']!=end-start or parsed['encoding']!=codec:
                raise ValueError('record mismatch')
            payload=parsed['payload'];count=payload[1]
            if codec in (10,13,16,22,25,28,40):
                from .animation_decoder import wide_channel_layout
                count,ticks,_=wide_channel_layout(payload)
                final_tick=ticks[-1] if ticks else 0
            elif codec in (11,14,17,23,26,29,41):
                mode=payload[1];mask=int.from_bytes(payload[2:2+(mode&63)],'little')
                final_tick=(mask.bit_length()-1)<<(mode>>6)
            else:
                final_tick=payload[count] if count>1 else 0
            resource=Resource([Channel(codec,payload,4 if codec in (39,40,41,54) else 8 if codec==66 else 16)])
            state=SampleState(0)
            for fraction in (0,.25,.5,.75,1,.5,0):
                time=final_tick/60*fraction;hint=int(time*60)
                state.hint=hint;out=[]
                sample_channel(resource,0,time,out,state,registered_channel_decoder)
                fresh=[];reset=SampleState(hint)
                sample_channel(resource,0,time,fresh,reset,registered_channel_decoder)
                if out!=fresh or state.cursor!=reset.cursor or not all(math.isfinite(v) for v in out):
                    raise ValueError('cursor consistency')
                samples+=1
            passed+=1
        except (ValueError,KeyError,TypeError,IndexError,OverflowError):
            # Do not export payload text or arbitrary exception messages.
            failures.append({'record':index,'codec':codec,'reason':'validation_failed'})
    return {'scope':'supplied-boundary decoding and cached/reset consistency; not native equivalence',
            'body_sha256':hashlib.sha256(body).hexdigest(),'records':len(records),
            'codec_counts':dict(sorted(counts.items())),
            'unsupported_codec_counts':{k:v for k,v in sorted(counts.items()) if k not in SUPPORTED},
            'unresolved_shared_records':shared,'validated_tracks':passed,
            'sample_checks':samples,'failures':failures,
            'all_tracks_supported_and_validated':passed==len(records),
            'game_payloads_included':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body',required=True,type=Path)
    parser.add_argument('--records',type=Path,help='optional explicit boundaries; otherwise parse clip body')
    args=parser.parse_args()
    body=args.body.read_bytes()
    if args.records:
        records=json.loads(args.records.read_text())
        if isinstance(records,dict):records=records['tracks']
    else:
        from .animation_container import parse_clip_body
        records=parse_clip_body(body)['tracks']
    result=inspect_clip(body,records)
    print(json.dumps(result,indent=2))
    return 1 if result['failures'] else 0


if __name__=='__main__':
    raise SystemExit(main())
