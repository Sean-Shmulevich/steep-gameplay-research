"""Offline resolved-input procedural-pose tail sequence runner.

Contract: docs/reconstruction/CENTRAL_IMPULSE.md, Composed active pose tail.
No native game access, provider inference, skeleton commit or world integration.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from reference.ground_response_pose import resolved_pose_tail


def run(request):
    if not isinstance(request, dict) or request.get('branch') != 'resolved_active_tail':
        raise ValueError('explicit resolved_active_tail branch required')
    frames = request.get('frames')
    if not isinstance(frames, list) or not 1 <= len(frames) <= 2400:
        raise ValueError('one to 2400 resolved-input frames required')
    state = copy.deepcopy(request.get('initial_state'))
    if not isinstance(state, dict) or set(state) != {'correction','endpoints'}:
        raise ValueError('initial correction and endpoint filter states required')
    encoded = json.dumps(request, sort_keys=True, separators=(',',':'), allow_nan=False)
    records = []
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict) or 'correction_previous' in frame or 'endpoint_previous' in frame:
            raise ValueError('frames must supply observations; filter state is carried by the runner')
        if frame.get('decay_mode') is not False:
            raise ValueError('resolved active branch requires decay_mode=false')
        blend = frame.get('blend')
        if type(blend) not in (int,float) or not math.isfinite(blend) or not 0 <= blend <= 1:
            raise ValueError('observed blend must be finite and within [0,1]')
        try:
            result = resolved_pose_tail(**frame, correction_previous=state['correction'],
                                        endpoint_previous=state['endpoints'])
        except (TypeError, IndexError, OverflowError) as exc:
            raise ValueError(f'invalid resolved inputs in frame {index}: {exc}') from exc
        state = result['state']
        records.append({'index':index, **result})
    return {'schema':1,'evidence':'reconstructed_local_math_with_supplied_observations',
            'input_sha256':hashlib.sha256(encoded.encode()).hexdigest(),
            'game_process':False,'provider_selection':False,'skeleton_commit':False,
            'limits':['Only the resolved active branch is represented.',
                      'Endpoint origins and contact observations remain caller inputs.',
                      'Filter state is carried; output positions are not fed back as physics.',
                      'Repeated inputs are not evidence of deterministic original-game replay.'],
            'records':records,'final_state':state}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--output')
    args = parser.parse_args()
    try:
        result = run(json.loads(Path(args.request).read_text()))
        text = json.dumps(result, indent=2, allow_nan=False)+'\n'
    except (ValueError, OSError) as exc:
        parser.exit(2, f'{exc}\n')
    if args.output:
        Path(args.output).write_text(text)
    else:
        print(text,end='')


if __name__ == '__main__':
    main()
