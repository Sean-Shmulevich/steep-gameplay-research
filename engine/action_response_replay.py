"""Offline directional-response sequence inspector; never accesses a process.

Run: python3 -m engine.action_response_replay input.json
Contract: docs/reconstruction/ACTION_RESPONSE_REPLAY.md.
"""
import argparse
from dataclasses import asdict
from functools import partial
import json
import math
from pathlib import Path
import struct
import sys
from .action_axis_ramp import AxisRampState, f32
from .action_curve_math import curve_acos, curve_cos
from .action_curve_roots import ordered_curve_roots
from .action_key_curve import CurveKey, evaluate_key_curve
from .action_response import directional_response


def _fields(value, names, label):
    if not isinstance(value, dict) or set(value) != set(names.split()):
        raise ValueError(f'{label} requires exactly: {names}')


def replay_response(document):
    """Replay explicit finite-domain settings and ticks; return JSON-safe receipts.

    Portable sqrt/power callbacks remain explicit in the output evidence label.
    Event order is supplied, not assigned a scheduler or wall-clock meaning.
    """
    _fields(document, 'schema provenance settings initial events', 'document')
    if document['schema'] != 'directional-response-v1':raise ValueError('unsupported schema')
    if not isinstance(document['provenance'], str) or not document['provenance'].strip():
        raise ValueError('nonempty caller provenance label required')
    settings = document['settings']
    _fields(settings, 'duration axis_mode keys input_bounds output_bounds', 'settings')
    initial = document['initial']
    _fields(initial, 'clock states', 'initial')
    if not isinstance(settings['keys'], list) or len(settings['keys']) > 64:
        raise ValueError('at most 64 keys required by inspector')
    keys = []
    for key in settings['keys']:
        _fields(key, 'x y incoming outgoing mode', 'key')
        keys.append(CurveKey(**key))
    if not isinstance(initial['states'], list) or len(initial['states']) > 8:
        raise ValueError('at most eight axis states required by inspector')
    for state in initial['states']:_fields(state, 'current remembered timer', 'state')
    states = tuple(AxisRampState(**state) for state in initial['states'])
    clock = f32(initial['clock'])
    events = document['events']
    if not isinstance(events, list) or not 1 <= len(events) <= 10000:
        raise ValueError('one to 10000 events required')
    duration = f32(settings['duration'])
    if duration <= 0:raise ValueError('positive duration required')
    mode = settings['axis_mode']
    if type(mode) is not int or not 0 <= mode < 1 << 32:raise ValueError('uint32 axis mode required')
    solver = partial(ordered_curve_roots, sqrt=math.sqrt, acos=curve_acos,
                     cos=curve_cos, power=math.pow)
    curve = partial(evaluate_key_curve, keys, input_bounds=settings['input_bounds'],
                    output_bounds=settings['output_bounds'], solve_roots=solver)
    previous_x = -math.inf
    for key in keys:
        if type(key.mode) is not int or not 0 <= key.mode < 1 << 32:
            raise ValueError('uint32 key mode required')
        if len(key.incoming) != 2 or len(key.outgoing) != 2:
            raise ValueError('two-lane control handles required')
        values = [f32(v) for v in (key.x, key.y, *key.incoming, *key.outgoing)]
        if values[0] < previous_x:raise ValueError('nondecreasing key positions required')
        previous_x = values[0]
    for name in ('input_bounds', 'output_bounds'):
        bounds = settings[name]
        if bounds is not None:
            if not isinstance(bounds, list) or len(bounds) != 2:
                raise ValueError('two bounds or null required')
            for value in bounds:f32(value)
    rows = []
    for index, event in enumerate(events):
        _fields(event, 'vector start_ticks end_ticks ramp_enabled diagonal_enabled global_gate configuration_available', 'event')
        for name in ('start_ticks', 'end_ticks'):
            tick = event[name]
            if tick is not None and (type(tick) is not int or not 0 <= tick < 1 << 64):
                raise ValueError(f'{name} must be uint64 or null')
        for name in ('ramp_enabled', 'diagonal_enabled'):
            if event[name] is not None and type(event[name]) is not bool:
                raise ValueError(f'{name} must be bool or null')
        for name in ('global_gate', 'configuration_available'):
            if type(event[name]) is not bool:raise ValueError(f'{name} must be bool')
        result = directional_response(states=states, previous_clock=clock,
                                      duration=duration, axis_mode=mode, curve=curve, **event)
        states, clock = result['states'], result['clock']
        rows.append(dict(index=index, output=result['output'],
                         output_hex=struct.pack('<4f', *result['output']).hex(),
                         states=[asdict(state) for state in states],
                         timer_hex=[struct.pack('<f', state.timer).hex() for state in states],
                         clock=clock, clock_hex=struct.pack('<f', clock).hex(),
                         curve_inputs=result['curve_inputs'],
                         stages=[dict(index=s.index, invoked=s.invoked, raw_hex=s.raw.hex(),
                                      working_hex=s.working.hex(), published_hex=s.published.hex())
                                 for s in result['stages']]))
    return dict(schema='directional-response-result-v1',
                caller_provenance=document['provenance'], game_process=False,
                math_policy='reconstructed acos/cos; portable Python sqrt/power rounded to float32',
                limits=['Caller supplies tuning, initial state and both clock reads',
                        'No device queries, action arbitration or scheduler placement',
                        'Finite-intermediate contract; no original-engine equivalence'],
                updates=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > 8 * 1024 * 1024:raise ValueError('input exceeds 8 MiB')
        result = replay_response(json.loads(args.input.read_text()))
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, TypeError, KeyError, OSError, OverflowError, ZeroDivisionError) as exc:
        print(f'Response inspection failed: {exc}', file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':raise SystemExit(main())
