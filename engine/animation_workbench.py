"""Offline JSON inspection API for the recovered animation work-transform kernels.

No game process, original assets, scheduler, pose publication or lifecycle actions.
Evidence: docs/reconstruction/ANIMATION_WORKBENCH.md.
"""
import argparse
import json
import math
from pathlib import Path
import sys
from reference.animation_work import (gather_work_transforms, gather_context_work,
                                     gather_raw_context_work)
from reference.snow import f32


def inspect_work(request):
    if isinstance(request,dict) and request.get('schema') == 'animation-update-input-v1':
        from engine.animation_update_workbench import inspect_update
        return inspect_update(request)
    if not isinstance(request, dict) or request.get('schema') != 'animation-work-input-v1':
        raise ValueError('expected animation-work-input-v1 object')
    allowed = {'schema', 'records', 'indices', 'parent_position', 'parent_rotation',
               'direct', 'context', 'normalization'}
    if set(request)-allowed:
        raise ValueError('unknown workbench input fields')
    required = {'records', 'indices', 'parent_position', 'parent_rotation', 'direct'}
    if not required <= request.keys():
        raise ValueError('missing bank inputs')
    if not isinstance(request['records'], list) or not isinstance(request['indices'], list):
        raise ValueError('record and index arrays required')
    if len(request['records']) > 4096 or len(request['indices']) > 4096:
        raise ValueError('inspection limit is 4096 records and selections')
    if type(request['direct']) is not bool:
        raise ValueError('boolean direct flag required')
    args = {key: request[key] for key in required}
    context = request.get('context')
    log = []
    seed_index = 0
    norm = request.get('normalization')
    seeds = []
    mode = 'not_used'
    if context is not None:
        if not isinstance(context, dict) or context.get('kind') not in ('raw', 'converted'):
            raise ValueError('context kind must be raw or converted')
        keys = {'kind', 'basis_rows', 'position'} if context['kind'] == 'raw' else {'kind', 'position', 'rotation'}
        if set(context) != keys:
            raise ValueError('context fields do not match its kind')
        if not isinstance(norm, dict):
            raise ValueError('context requires an explicit normalization policy')
        mode = norm.get('mode')
        if mode == 'provided_seeds':
            if set(norm) != {'mode', 'seeds'} or not isinstance(norm['seeds'], list):
                raise ValueError('provided_seeds requires a seed array')
            seeds = norm['seeds']
            if len(seeds) != len(request['indices']) + (context['kind'] == 'raw'):
                raise ValueError('seed count must match raw conversion plus output rotations')
            if any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in seeds):
                raise ValueError('positive finite seeds required')
        elif mode != 'exact_rsqrt_substitute' or set(norm) != {'mode'}:
            raise ValueError('choose provided_seeds or exact_rsqrt_substitute explicitly')
    elif norm is not None:
        raise ValueError('normalization is unused without context')

    def rsqrt(n):
        nonlocal seed_index
        seed = seeds[seed_index] if mode == 'provided_seeds' else 1/math.sqrt(n)
        seed = f32(seed)
        if not math.isfinite(seed) or seed <= 0:
            raise ValueError('seed must remain positive finite in float32')
        log.append(dict(index=seed_index, norm_squared=n, seed=seed))
        seed_index += 1
        return seed

    if context is None:
        output = gather_work_transforms(**args)
        path = 'no_visible_context_target'
    elif context['kind'] == 'raw':
        output = gather_raw_context_work(**args, basis_rows=context['basis_rows'],
                     position=context['position'], reciprocal_sqrt=rsqrt)
        path = 'raw_context_to_relative_work'
    else:
        output = gather_context_work(**args, context_position=context['position'],
                     context_rotation=context['rotation'], reciprocal_sqrt=rsqrt)
        path = 'converted_context_to_relative_work'
    if any(not math.isfinite(x) for row in output for vector in row.values() for x in vector):
        raise ValueError('nonfinite output rejected by inspection adapter')
    return dict(schema='animation-work-output-v1', path=path, transforms=output,
                normalization=dict(mode=mode, calls=log,
                    supplied_seed_provenance_verified=False,
                    numerical_substitute=mode == 'exact_rsqrt_substitute'),
                evidence=dict(local_kernels='original-instruction-validated on synthetic cases',
                    this_input_game_verified=False, original_engine_equivalence=False,
                    scheduler_executed=False, live_memory_access=False,
                    pose_published=False, lifetime_established=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.input.stat().st_size > 4*1024*1024:
            raise ValueError('input exceeds 4 MiB inspection limit')
        def invalid_constant(value):
            raise ValueError('nonstandard JSON number: '+value)
        request = json.loads(args.input.read_text(), parse_constant=invalid_constant)
        result = inspect_work(request)
        text = json.dumps(result, indent=2, allow_nan=False)+'\n'
        if args.output:
            args.output.write_text(text)
        else:
            print(text, end='')
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, OSError) as exc:
        print(json.dumps(dict(ok=False, error=str(exc))), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
