"""Summarize private update JSONL without exporting pointers or body payloads.

Timing relation: docs/reconstruction/SCHEDULER_SMOOTHING_AUDIT.md and
engine/scheduler.py subdivision: elapsed = f32(consumed / f32(count)).
A matching observed group is not proof of a native substep index or full policy.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import struct


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def counter_changes(records):
    """Optional ABI-v2 marker; unsigned deltas preserve signed wrap semantics."""
    deltas = Counter()
    unavailable = invalid = 0
    for record in records:
        before, after = record['before'], record['after']
        if 'preconsume_counter' not in before or 'preconsume_counter' not in after:
            unavailable += 1
            continue
        values = (before['preconsume_counter'], after['preconsume_counter'])
        if (not (before['valid'] & 1 and after['valid'] & 1)
                or any(type(x) is not int or not -(1 << 31) <= x < (1 << 31) for x in values)
                or any(before[k] != after[k] for k in ('runtime', 'main', 'rider'))):
            invalid += 1
            continue
        deltas[(values[1] - values[0]) & 0xffffffff] += 1
    return {'available_pairs': sum(deltas.values()), 'unavailable_pairs': unavailable,
            'invalid_pairs': invalid, 'decrement_by_one_pairs': deltas[0xffffffff],
            'unchanged_pairs': deltas[0], 'unsigned_delta_histogram': dict(sorted(deltas.items())),
            'consumer_execution_proved': False}


def analyze(rows):
    if not rows or rows[0].get('kind') != 'summary':
        raise ValueError('Missing capture summary')
    summary, records = rows[0], rows[1:]
    if type(summary.get('records')) is not int or summary['records'] != len(records):
        raise ValueError('Incomplete record export')
    groups = []
    rejected = 0
    previous = None
    for index, record in enumerate(records):
        if record.get('kind') != 'record' or record.get('index') != index:
            raise ValueError('Record indices must be unique and consecutive')
        before, after = record['before'], record['after']
        valid = (before['valid'] & 5 == 5 and after['valid'] & 5 == 5
                 and before['request'] == after['request'])
        for key in ('elapsed', 'derivative'):
            value = record.get(key)
            valid = valid and type(value) in (int, float) and math.isfinite(value) and value > 0
        if not valid:
            rejected += 1
            previous = None
            continue
        # Include ownership identity internally so counter reuse cannot merge actors.
        key = (record['actor'], before['runtime'], before['main'], before['rider'], before['request'])
        if any(before[k] != after[k] for k in ('runtime', 'main', 'rider')):
            rejected += 1
            previous = None
            continue
        if key != previous:
            groups.append([])
        groups[-1].append(record)
        previous = key
    exact = 0
    mismatched = 0
    histogram = Counter()
    for group in groups:
        count = len(group)
        histogram[count] += 1
        consumed = f32(group[0]['derivative'])
        match = all(f32(r['derivative']) == consumed and
                    f32(r['elapsed']) == f32(consumed / f32(count)) for r in group)
        exact += int(match)
        mismatched += int(not match)
    return {
        'preconsume_counter': counter_changes(records),
        'records': len(records), 'rejected_timing_records': rejected,
        'observed_request_groups': len(groups),
        'records_per_group': dict(sorted(histogram.items())),
        'float32_subdivision_matching_groups': exact,
        'nonmatching_or_partial_groups': mismatched,
        'loss_free_export': summary.get('dropped') == 0,
        'slot_lifecycle_passed': all(summary.get(k) == 1 for k in ('installed', 'restored', 'drained')),
        'direct_native_substep_index_used': False,
        'limits': ['Groups at capture edges or gaps can be partial.',
                   'Matching duration arithmetic does not recover smoothing history or frequency selection.',
                   'Record order is reservation order; concurrent calls can complicate grouping.',
                   'No pointer or raw body payload is included in this summary.'],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = analyze([json.loads(line) for line in args.trace.read_text().splitlines()])
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end='')
