"""Offline composition of recovered curve, jump-state and central-impulse kernels.

The JSON scenario and serial orchestration are authored. No contact solver,
animation, live game access or original-engine equivalence.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from reference.central_impulse import central_impulse, f32
from reference.runtime_curve import compile_samples, evaluate
from reference.snow_jump_step import jump_step
from reference.snow_charge_release import update_release
from reference.input_cooker import cook
from reference.decay_table import build as build_decay_table
from reference.decay_exp import cooker_table


def run(document):
    if document.get('schema') != 'snow-jump-bench-v1' or document.get('provenance') != 'authored_synthetic':
        raise ValueError('Explicit snow-jump-bench-v1 authored_synthetic scenario required')
    values = deepcopy(document)
    frames = values['frames']
    if not isinstance(frames,list) or not 1 <= len(frames) <= 10000:
        raise ValueError('Provide 1..10000 frames')
    bodies = values['bodies']
    if set(bodies) not in ({'main'}, {'main','rider'}):
        raise ValueError('Main and optional rider bodies required')
    for body in bodies.values():
        # Validate and normalize without changing the supplied velocities.
        checked = central_impulse(**body, impulse=(0,0,0), force=False)
        body['linear'] = checked['linear']; body['angular'] = checked['angular']
    state = {k:f32(values['state'][k]) for k in ('cached_factor','cooldown')}
    config = values['config']
    curves = {key:compile_samples(**values['curves'][key]) for key in ('coil','depth','speed')}
    release_state = values.get('release_state')
    cooker = values.get('cooker')
    decay_table = None
    if cooker is not None:
        if release_state is None:
            raise ValueError('Cooker requires release_state')
        decay = cooker['decay']
        if decay.get('mode', 'supplied_samples') == 'reconstructed_default':
            if set(decay) != {'mode', 'vector_path', 'scalar_path'}:
                raise ValueError('Reconstructed default requires only mode and explicit CPU paths')
            decay_table = cooker_table(vector_path=decay['vector_path'], scalar_path=decay['scalar_path'])
        elif decay.get('mode', 'supplied_samples') == 'supplied_samples':
            if decay.get('provenance') != 'authored_synthetic':
                raise ValueError('Explicit authored_synthetic decay samples required')
            decay_table = build_decay_table(decay['samples'], low=decay['low'],
                                           high=decay['high'], padding=decay['padding'])
        else:
            raise ValueError('Unknown decay mode')
    trace = []
    for index, frame in enumerate(frames):
        release_before = deepcopy(release_state)
        cooker_result = None
        if f32(frame['elapsed_dt']) <= 0:
            raise ValueError('Positive elapsed_dt required by bench policy')
        if cooker is not None:
            if 'cooked' in frame:
                raise ValueError('Choose cooker or explicit cooked input, not both')
            if f32(frame['cooker_dt']) <= 0:
                raise ValueError('Positive cooker_dt required by bench policy')
            cooker_result = cook(release_state['cooked'], frame['cooker_target'],
                frame['cooker_dt'], cooker['coefficients'], epsilon=cooker['epsilon'],
                decay_lookup=lambda argument: evaluate(argument, **decay_table))
            frame['cooked'] = cooker_result['value']
        if release_state is not None:
            if 'release_signal' in frame:
                raise ValueError('Choose explicit release_signal or release_state, not both')
            release_state=update_release(release_state, new_cooked=frame['cooked'],
                raw_remapped_charge=frame['raw_remapped_charge'],elapsed_dt=frame['elapsed_dt'],
                derivative_dt=frame['derivative_dt'],release_threshold=config['release_threshold'],
                input_update_mode=frame['input_update_mode'])
            frame['release_signal']=release_state['release_signal']
        # Curves are pure diagnostic preprocessing here, not proof of native visits.
        gains = {key:evaluate(frame[field],**curves[key]) for key,field in
                 (('coil','release_signal'),('depth','depth'),('speed','projected_speed'))}
        before = deepcopy(bodies)
        old_state = dict(state)
        result = jump_step(**state, elapsed_dt=frame['elapsed_dt'],air_time=frame['air_time'],
                           release_signal=frame['release_signal'],base_factor=config['base_factor'],
                           gravity=config['gravity'],combined_mass=config['combined_mass'],
                           configured_rider_mass=config['configured_rider_mass'],rider_present='rider' in bodies,
                           coil_gain=gains['coil'],depth_gain=gains['depth'],speed_gain=gains['speed'])
        applications = []
        for request in result['submissions']:
            name=request['body']; body=bodies[name]
            applied=central_impulse(**body,impulse=request['impulse'],force=request['force'])
            body['linear']=applied['linear']; body['angular']=applied['angular']
            applications.append({'body':name,'impulse':request['impulse'],**applied})
        state = {key:result[key] for key in ('cached_factor','cooldown')}
        trace.append({'index':index,'cooker':cooker_result,'release_state_before':release_before,
                      'release_state_after':deepcopy(release_state),'gains':gains,'branch':result['branch'],
                      'state_before':old_state,'state_after':dict(state),
                      'bodies_before':before,'bodies_after':deepcopy(bodies),'applications':applications})
    return {'schema':'snow-jump-bench-result-v1','provenance':'authored_synthetic',
            'game_access':False,'decay_configuration':deepcopy(cooker['decay']) if cooker else None,'trace':trace,'final_state':state,'final_bodies':bodies,'final_release_state':release_state,
            'limits':['Inputs, clocks, depth, speed, masses and optional decay samples are supplied scenario data.',
                      'Cooker-to-release orchestration is authored; native scheduling and live CPU dispatch remain unverified.',
                      'Curve preprocessing is not a record of native curve visits.',
                      'No gravity integration, contacts, constraints, dispatch or animation is simulated.',
                      'Preserved angular velocity covers central arithmetic only.']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario',type=Path); parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    output=json.dumps(run(json.loads(args.scenario.read_text())),indent=2,allow_nan=False)+'\n'
    if args.output: args.output.write_text(output)
    else: print(output,end='')
