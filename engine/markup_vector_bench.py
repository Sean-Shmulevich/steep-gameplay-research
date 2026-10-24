"""Offline vector-to-pending inspection; no game access or inferred transitions.

See CENTRAL_IMPULSE.md, Runnable vector-to-pending inspection.
"""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
from .markup_vector_dispatch import select_vector_route, dispatch_vector
from .markup_snow_vector import snow_vector, branch3_vector
from .markup_pending import queue_world_scaled_pending
from reference.central_impulse import f32


def inspect(document):
    if document.get('schema') != 'markup-vector-bench-v1':
        raise ValueError('markup-vector-bench-v1 schema required')
    if document.get('provenance') not in ('authored_synthetic','caller_supplied_observation'):
        raise ValueError('explicit provenance required')
    data=deepcopy(document)
    state=data['post_dispatch_state']
    mode,outer,inner=(state.get(k) for k in ('current_mode','outer_state','inner_state'))
    decision=select_vector_route(mode,outer,inner)
    # ID 84 initializes the temporary before invoking its vector service.
    vector=[0.0]*4
    seed_requests=[]
    def seed(squared):
        seed_requests.append(squared)
        if 'rsqrt_seed' not in data:
            raise ValueError('explicit hardware/emulator or synthetic RSQRT seed required')
        value=data['rsqrt_seed']
        return math.inf if value=='positive_infinity' else f32(value)
    def invoke(route,depth,out):
        inputs=data['vector_inputs']
        if route.startswith('projection_'):
            xyz=snow_vector(inputs['direction'],inputs['normal'],inputs['gain'],seed)
        else:
            xyz=branch3_vector(inputs['current'],inputs['normal'],inputs['entity_direction'],
                inputs['gain'],direct_direction=inputs['direct_direction'],
                reverse_fallback=inputs['reverse_fallback'],reciprocal_sqrt_seed=seed)
        out[:]=xyz+[0.0]  # Explicit XYZ-only composition, not native W-bit proof.
    returned=dispatch_vector(mode,outer,inner,vector,invoke)
    finite=all(math.isfinite(x) for x in vector)
    pending_after=None
    if finite:
        pending_after=list(queue_world_scaled_pending(data['pending_before'],vector,data['world_interval']))
    def encode(value):
        if math.isnan(value):return 'nan'
        if math.isinf(value):return 'positive_infinity' if value>0 else 'negative_infinity'
        return value
    return dict(schema='markup-vector-result-v1',provenance=data['provenance'],
        route=decision,dispatcher_return=returned,vector=[encode(v) for v in vector],
        rsqrt_squared_lengths=[encode(v) for v in seed_requests],pending_after=pending_after,
        status='computed' if finite else 'nonfinite_vector_pending_not_evaluated',
        boundaries=['post-dispatch state supplied, not inferred',
                    'actor/entity/runtime/world guards assumed already satisfied',
                    'XYZ formula composition with authored zero W',
                    'no deferred transitions, callback execution, physics consumption or velocity update',
                    'supplied RSQRT seed is not verified against live hardware'])


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
