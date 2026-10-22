"""JSON sequence runner for the reconstructed ground-response helper.

Run python3 -m engine.ground_response_bench --request request.json.
Caller supplies observations and curves; no game files, hooks or body writes.
"""
import argparse
from dataclasses import asdict
from functools import partial
import hashlib
import json
import math
from pathlib import Path
from reference.central_impulse import f32, vector
from reference.ground_response import HelperState, compile_curves, update
from reference.runtime_curve import evaluate


def run(request):
    if not isinstance(request, dict):
        raise ValueError('ground-response request must be an object')
    policy = request['rsqrt_policy']
    if policy not in ('supplied', 'sqrt_seed'):
        raise ValueError('choose supplied or sqrt_seed explicitly')
    frames = request['frames']
    if not isinstance(frames, list) or not 1 <= len(frames) <= 2400:
        raise ValueError('provide 1..2400 frames')
    initial = request['initial_state']
    state = HelperState(vector(initial['previous_velocity']),vector(initial['current_velocity']),
                        f32(initial['rate']),f32(initial['displacement']))
    curve_format = request['curve_format']
    if curve_format == 'sampled':
        for field in ('forceSpeedCurve','legCoilCurve','forceDepthCurve'):
            samples = request['curves'][field]['$array']
            if not isinstance(samples,list) or not 2 <= len(samples) <= 4097:
                raise ValueError('sampled curves require 2..4097 samples')
        curves = compile_curves(request['curves'])
    elif curve_format == 'compiled':
        curves = {}
        for role in ('entry','a','b'):
            c = request['curves'][role]
            segments = c['segments']
            if not isinstance(segments,list) or not 1 <= len(segments) <= 4096:
                raise ValueError('compiled curves require 1..4096 segments')
            table = dict(start=f32(c['start']),index_scale=f32(c['index_scale']),
                         segments=tuple(tuple(map(f32,s)) for s in segments))
            if table['index_scale'] <= 0 or any(len(s)!=2 for s in table['segments']):
                raise ValueError('invalid compiled curve table')
            curves[role] = partial(evaluate,**table)
    else:
        raise ValueError('curve_format must be sampled or compiled')
    records = []
    elapsed = 0.
    for index, frame in enumerate(frames):
        observation = frame['observation']
        dt = observation['dt']
        if type(dt) not in (int,float) or not math.isfinite(dt) or not 0 < dt <= 1:
            raise ValueError('testbench dt must be in (0,1] seconds')
        estimates = frame.get('rsqrt_estimates',[])
        if not isinstance(estimates,list):
            raise ValueError('rsqrt_estimates must be an array')
        supplied = iter(estimates)
        used = []
        def seed(n):
            if policy == 'sqrt_seed':
                value = f32(1/math.sqrt(n))
            else:
                try:
                    value = f32(next(supplied))
                except StopIteration as exc:
                    raise ValueError(f'frame {index}: missing reciprocal-square-root estimate') from exc
            if value <= 0:
                raise ValueError('positive reciprocal-square-root estimate required')
            used.append(value)
            return value
        if policy == 'sqrt_seed' and estimates:
            raise ValueError('sqrt_seed policy must not include supplied estimates')
        result = update(state,observation,curves,seed,force=frame['force'],submission=frame['submission'])
        exhausted = object()
        if policy == 'supplied' and next(supplied,exhausted) is not exhausted:
            raise ValueError(f'frame {index}: unused reciprocal-square-root estimates')
        state = result['state']
        elapsed += dt
        record = dict(result,index=index,elapsed_seconds=elapsed,rsqrt_estimates_used=used)
        record['state'] = asdict(state)
        records.append(record)
    canonical = json.dumps(request,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return {'schema':1,'evidence':'reconstructed_helper_with_caller_supplied_inputs',
            'live_game_execution':False,'body_mutations':False,'rsqrt_policy':policy,
            'numerical_limit':'sqrt_seed is a derived estimate; supplied estimates are caller data, not automatically verified native observations',
            'input_sha256':hashlib.sha256(canonical).hexdigest(),'frames':records,'final_state':asdict(state)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True,type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=run(json.loads(args.request.read_text()))
    text=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(text)
    else:print(text,end='')


if __name__=='__main__':main()
