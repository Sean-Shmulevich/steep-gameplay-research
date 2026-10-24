"""Run the reconstructed snow basis callback from explicit JSON inputs."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import struct
from reference.central_impulse import f32
from reference.runtime_curve import evaluate
from .snow_slope_angle import build_slope_angle_table, evaluate_slope_angle
from .snow_basis_callback import basis_callback

BOUNDARIES = [
    'Entry state coherence and callback reachability are caller assertions',
    'Profile curves and runtime fields are supplied, not resolved from game objects',
    'Platform math is approximate; supplied sequences establish no provenance by themselves',
    'Protected invalid configuration and singular/nonfinite arithmetic are excluded',
    'No scheduler, body mutation, position integration or live game access',
]


def inspect(document):
    if document.get('schema')!='snow-basis-bench-v1':
        raise ValueError('snow-basis-bench-v1 schema required')
    if document.get('provenance') not in ('authored_synthetic','caller_supplied_observation'):
        raise ValueError('Explicit provenance required')
    if document.get('phase_continuity')!='caller_asserted_stable_inputs':
        raise ValueError('Explicit entry consistency assertion required')
    if type(document.get('callback_reached')) is not bool:
        raise ValueError('Explicit callback_reached boolean required')
    data=deepcopy(document)
    result=dict(schema='snow-basis-result-v1',provenance=data['provenance'],
                phase_continuity=data['phase_continuity'],boundaries=list(BOUNDARIES))
    if not data['callback_reached']:
        return dict(**result,status='not_evaluated')
    spec=data['math'];mode=spec['mode'];calls=[];table=None
    if mode not in ('platform_approximation','supplied_sequence'):
        raise ValueError('Explicit supported math mode required')
    if mode=='supplied_sequence' and not isinstance(spec.get('calls'),list):
        raise ValueError('Ordered supplied calls required')
    def sample(kind,value):
        nonlocal table
        value=f32(value)
        if mode=='supplied_sequence':
            index=len(calls)
            if index>=len(spec['calls']):raise ValueError('Supplied math sequence exhausted')
            item=spec['calls'][index]
            if item['kind']!=kind or struct.pack('<f',f32(item['input']))!=struct.pack('<f',value):
                raise ValueError('Supplied math call kind/input mismatch')
            output=f32(item['value'])
        elif kind=='slope_angle':
            if table is None:
                table=build_slope_angle_table(lambda xs:[math.acos(x) for x in xs],math.acos)
            output=evaluate_slope_angle(value,table)
        elif kind=='sin':output=f32(math.sin(value))
        elif kind=='cos':output=f32(math.cos(value))
        else:output=f32(1/math.sqrt(value))
        if not math.isfinite(value) or not math.isfinite(output):
            raise ValueError('Finite math inputs and results required')
        calls.append(dict(kind=kind,input=value,value=output))
        return output
    curves={name:(lambda x,curve=curve:evaluate(x,**curve))
            for name,curve in data.get('curves',{}).items()}
    effects=basis_callback(data['enabled_byte'],data['incoming_basis'],
                           data.get('prepass'),data.get('overrides'),curves,
                           lambda x:sample('slope_angle',x),lambda x:sample('sin',x),
                           lambda x:sample('cos',x),lambda x:sample('rsqrt',x))
    if mode=='supplied_sequence' and len(calls)!=len(spec['calls']):
        raise ValueError('Unused supplied math observations')
    return dict(**result,status='evaluated',math_mode=mode,math_calls=calls,effects=effects)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=inspect(json.loads(args.input.read_text()))
    text=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(text)
    else:print(text,end='')


if __name__=='__main__':main()
