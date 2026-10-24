"""Inspect reconstructed snow velocity stages with explicit supplied state.

Contract: CENTRAL_IMPULSE.md, Runnable contact-volume to velocity inspection.
No body mutation, game payload, native scheduling or implicit profile fallback.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from .body_velocity_limits import initialized_velocity_limits
from .snow_profile_selection import select_volume_profile
from .snow_velocity_correction import (
    select_velocity_decay_drive, evaluate_velocity_decay_profile,
    correct_linear_velocity, build_velocity_decay_sampler,
)

BOUNDARIES = [
    'Reachability and consistency across native phases are caller assertions',
    'Completed volume map, resolved curves, frames and runtime inputs are supplied',
    'Explicit CPU arithmetic path does not establish native live CPU dispatch',
    'Result ends before native velocity assignment, subsequent impulses and solver',
    'No geometry update, position integration, input device mapping or live game access',
]


def inspect(document):
    if document.get('schema') != 'snow-velocity-bench-v1':
        raise ValueError('snow-velocity-bench-v1 schema required')
    if document.get('provenance') not in ('authored_synthetic','caller_supplied_observation'):
        raise ValueError('Explicit provenance required')
    if document.get('phase_continuity') != 'caller_asserted_stable_inputs':
        raise ValueError('Explicit phase consistency assertion required')
    if type(document.get('stages_reached')) is not bool:
        raise ValueError('Explicit stages_reached boolean required')
    data=deepcopy(document)
    result=dict(schema='snow-velocity-result-v1',provenance=data['provenance'],
                phase_continuity=data['phase_continuity'],boundaries=list(BOUNDARIES))
    if not data['stages_reached']:
        return dict(**result,status='not_evaluated',reason='Caller reports stages not reached')
    selection=select_volume_profile(data['profile_volumes'])
    registry={}
    for item in data['base_curves']:
        key=item['profile_key']
        if type(key) is not int or not 0 < key < 1<<64 or key in registry:
            raise ValueError('Unique nonzero uint64 curve identities required')
        registry[key]=item['curve']
    drive=select_velocity_decay_drive(**data['drive'])
    profile=evaluate_velocity_decay_profile(
        **data['profile'],base_curve=registry.get(selection['profile_key']),
        additive_rate=drive['additive_rate'])
    if data['bounds_source'] == 'initializer_defaults':
        if 'bounds' in data:
            raise ValueError('Initializer mode cannot also supply bounds')
        defaults=initialized_velocity_limits()
        lower,upper=defaults['linear_lower'],defaults['linear_upper']
    elif data['bounds_source'] == 'supplied':
        lower,upper=data['bounds']['lower'],data['bounds']['upper']
    else:
        raise ValueError('Explicit initializer_defaults or supplied bounds source required')
    sample=build_velocity_decay_sampler(**data['decay_cpu'])
    correction=correct_linear_velocity(
        **data['velocity'],rates=profile['rates'][:3],sample_decay=sample,
        disabled=profile['contact_correction_disabled'],
        bypass=drive['speed_floor_bypassed'],lower=lower,upper=upper)
    return dict(**result,status='evaluated',profile_selection=selection,drive=drive,
                profile=profile,correction=correction,bounds_source=data['bounds_source'],
                bounds=dict(lower=lower,upper=upper),decay_cpu=data['decay_cpu'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=inspect(json.loads(args.input.read_text()))
    text=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(text)
    else:print(text,end='')


if __name__ == '__main__':
    main()
