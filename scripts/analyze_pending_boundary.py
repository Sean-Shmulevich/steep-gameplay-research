"""Summarize private 35-column callback observations without exporting addresses.

Sequential snapshots are not atomic. Callback boundaries do not identify the
exact queue producer or consumer instruction. Input remains private.
"""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import statistics


def analyze(text):
    headers = {}
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if '=' in line:
            key, value = line.split('=', 1)
            headers[key] = value
            continue
        fields = line.split()
        if len(fields) != 35:
            raise ValueError('Expected 35 columns')
        row = [int(x) for x in fields[:17]] + [float(x) for x in fields[17:]]
        if not all(math.isfinite(x) for x in row[17:]):
            raise ValueError('Non-finite sample')
        rows.append(row)
    qpf = int(headers['qpf'])
    if qpf <= 0:
        raise ValueError('Invalid timer frequency')
    groups = defaultdict(list)
    samples = []
    for row in rows:
        if row[2] == 2 or (row[2] in (0, 1) and row[3] == 1):
            groups[row[7] if row[2] == 2 else row[5]].append(row)
            samples.append(row)
    rejection = Counter()
    counts = Counter()
    states = Counter()
    changed_states = Counter()
    accepted = {}
    for request, group in groups.items():
        if Counter(r[2] for r in group) != {0: 1, 1: 1, 2: 1}:
            rejection['missing_or_duplicate_boundary'] += 1
            continue
        entry, leave, step = sorted(group, key=lambda r: r[2])
        if not entry[0] <= leave[0] <= step[0]:
            rejection['timestamp_order'] += 1
            continue
        if any((r[10] & (15 if r[13] else 7)) != (15 if r[13] else 7) for r in group):
            rejection['invalid_sample'] += 1
            continue
        if len({tuple(r[11:14]) for r in group}) != 1:
            rejection['object_changed'] += 1
            continue
        accepted[request] = (entry, leave, step)
        counts['matched_requests'] += 1
        if entry[17:21] != leave[17:21] and entry[10] & 16 and leave[10] & 16:
            changed_states[f'{entry[15]}:{entry[16]} -> {leave[15]}:{leave[16]}'] += 1
        for name, row in zip(('entry', 'return', 'world_step_entry'), (entry, leave, step)):
            counts[name + '_pending_nonzero'] += any(x != 0 for x in row[17:21])
            if row[10] & 16:
                states[f'{row[15]}:{row[16]}'] += 1
        counts['pending_changed_during_actor_callback'] += entry[17:21] != leave[17:21]
        counts['pending_changed_before_world_step'] += leave[17:21] != step[17:21]
        counts['main_velocity_changed_during_actor_callback'] += entry[21:27] != leave[21:27]
        counts['rider_velocity_changed_during_actor_callback'] += entry[27:33] != leave[27:33]
    next_counts = Counter()
    for request, (_, _, step) in accepted.items():
        following = accepted.get((request + 1) & 0xffffffff)
        if not following or not any(step[17:21]):
            continue
        entry = following[0]
        if entry[0] < step[0] or entry[11:14] != step[11:14]:
            continue
        next_counts['nonzero_step_with_next_actor_entry'] += 1
        if not any(entry[17:21]):
            next_counts['zero_by_next_actor_entry'] += 1
        elif entry[17:21] == step[17:21]:
            next_counts['unchanged_at_next_actor_entry'] += 1
        else:
            next_counts['changed_nonzero_at_next_actor_entry'] += 1
    times = sorted(r[14] * 1e6 / qpf for r in samples)
    good_bodies = [r for r in samples if r[10] & 7 == 7]
    def magnitudes(start, stop):
        values = [math.sqrt(sum(x*x for x in r[start:stop])) for r in good_bodies]
        return {'min': min(values), 'max': max(values)} if values else None
    expected = int(headers['records'])
    dropped = int(headers['dropped'])
    if expected < len(rows) or dropped < 0:
        raise ValueError('Invalid record accounting')
    return {
        'schema': 1, 'evidence': 'callback_boundary_observation',
        'status': headers.get('status'), 'rows': len(rows),
        'incomplete_records': expected - len(rows), 'dropped': dropped,
        'recording_complete': headers.get('status') == 'restored' and dropped == 0 and expected == len(rows),
        'sampled_rows': len(samples), 'request_groups': len(groups),
        'main_speed_raw_units': magnitudes(21, 24),
        'main_angular_speed_raw_units': magnitudes(24, 27),
        'counts': dict(counts), 'rejected_groups': dict(rejection),
        'state_variant_observations': dict(states),
        'pending_change_state_pairs': dict(changed_states),
        'next_request_observations': dict(next_counts),
        'snapshot_cost_us': {
            'median': statistics.median(times),
            'p95': times[max(0, math.ceil(len(times)*.95)-1)], 'max': max(times)
        } if times else None,
        'limits': ['Sequential reads are not atomic or lifetime-pinned.',
                   'No direct queue-call or consumer-call interception.',
                   'Zero pending at boundaries does not prove no impulse occurred.',
                   'Object identity does not establish active body membership.'],
    }



def qualify_input_window(recording, input_log):
    """Align OS-delivery events with recorded world-step timestamps.

    Reports coverage only; key delivery is not game acceptance and final speed
    does not establish why a rider slowed or whether it remained stopped.
    """
    checked = analyze(recording)
    headers = dict(line.split('=', 1) for line in recording.splitlines() if '=' in line)
    frequency = int(headers['qpf'])
    steps = []
    for line in recording.splitlines():
        if not line.strip() or '=' in line:
            continue
        fields = line.split()
        if int(fields[2]) == 2:
            steps.append(fields)
    if not steps:
        raise ValueError('No world-step boundary observations')
    steps.sort(key=lambda r: int(r[0]))
    first, last = int(steps[0][0]), int(steps[-1][0])
    events = []
    for line in input_log.splitlines():
        if not line.startswith('{'):
            continue
        event = json.loads(line)
        if event.get('kind') not in ('hold_start', 'hold_complete'):
            continue
        if event.get('qpc_frequency') != frequency:
            raise ValueError('Input and recorder clocks differ')
        tick = event['qpc_ticks']
        if type(tick) is not int:
            raise ValueError('Invalid input timestamp')
        events.append(event)
    starts = [e for e in events if e['kind'] == 'hold_start']
    ends = [e for e in events if e['kind'] == 'hold_complete']
    single = len(starts) == len(ends) == 1
    covered = single and first <= starts[0]['qpc_ticks'] <= ends[0]['qpc_ticks'] <= last
    released = single and ends[0].get('all_injected_keys_released') is True
    valid_last = int(steps[-1][10]) & 7 == 7
    return {
        'evidence': 'os_input_and_callback_clock_alignment',
        'recording_complete': checked['recording_complete'],
        'recorded_seconds': (last-first)/frequency,
        'hold_starts': len(starts), 'hold_completions': len(ends),
        'exactly_one_complete_pulse_covered': bool(covered and released),
        'input_events': [dict(kind=e['kind'], seconds_from_first_step=(e['qpc_ticks']-first)/frequency)
                         for e in events],
        'post_release_recorded_seconds': (last-ends[0]['qpc_ticks'])/frequency if covered and released else None,
        'last_main_speed_raw_units': math.sqrt(sum(float(v)**2 for v in steps[-1][21:24])) if valid_last else None,
        'limits': ['OS input delivery does not prove game acceptance.',
                   'Final speed does not prove a lasting stop or identify its cause.'],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--input-log', type=Path)
    args = parser.parse_args()
    recording = args.input.read_text()
    result = analyze(recording)
    if args.input_log:
        result['input_window'] = qualify_input_window(recording, args.input_log.read_text())
    print(json.dumps(result, indent=2))
