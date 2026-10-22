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


def countdown_changes(records):
    """Legacy preconsume_timers[1] is the countdown; [0] is not a timer."""
    counts = Counter()
    for record in records:
        before, after = record['before'], record['after']
        arrays = (before.get('preconsume_timers'), after.get('preconsume_timers'))
        if any(not isinstance(x, list) or len(x) != 2 for x in arrays):
            counts['unavailable_pairs'] += 1
            continue
        values = [arrays[0][1], arrays[1][1], record.get('elapsed'), record.get('derivative')]
        if (not (before['valid'] & 1 and after['valid'] & 1)
                or any(before[k] != after[k] for k in ('runtime','main','rider'))
                or any(type(x) not in (int,float) or not math.isfinite(x) for x in values)):
            counts['invalid_pairs'] += 1
            continue
        old, new, elapsed, consumed = map(f32, values)
        counts['available_pairs'] += 1
        counts['elapsed_subtraction_matches'] += int(new == f32(old - elapsed))
        counts['consumed_subtraction_matches'] += int(new == f32(old - consumed))
        if elapsed != consumed:
            counts['distinct_clock_pairs'] += 1
            counts['distinct_elapsed_matches'] += int(new == f32(old - elapsed))
            counts['distinct_consumed_matches'] += int(new == f32(old - consumed))
    return {k: counts[k] for k in ('available_pairs','unavailable_pairs','invalid_pairs',
            'elapsed_subtraction_matches','consumed_subtraction_matches','distinct_clock_pairs',
            'distinct_elapsed_matches','distinct_consumed_matches')}


def interval_order(records):
    """Observed wrapper intervals only; no scheduler exclusion or ownership proof.

    Compare per actor, not per body identity: a rebinding during a call must not
    hide an overlapping invocation. Closed intervals that merely touch are not
    counted as overlap. Equal ticks cannot resolve ordering below clock precision.
    """
    actors = {}
    missing = invalid = zero = 0
    for r in records:
        if any(k not in r for k in ('entry', 'exit', 'thread')):
            missing += 1
            continue
        start, end, thread = r['entry'], r['exit'], r['thread']
        if (any(type(x) is not int or x < 0 or x >= 1 << 64
                for x in (start, end, thread)) or end < start):
            invalid += 1
            continue
        if end == start:
            zero += 1
        actors.setdefault(r['actor'], []).append(r)
    overlaps = migrations = adjacent = reservation_reversals = 0
    for group in actors.values():
        reservation_reversals += sum(b['entry'] < a['entry']
                                    for a, b in zip(group, group[1:]))
        ordered = sorted(group, key=lambda r: (r['entry'], r['index']))
        # Retain every prior end, so a long enclosing call is not missed when
        # the immediately preceding short call has already returned.
        import heapq
        active = []
        for r in ordered:
            while active and active[0] <= r['entry']:
                heapq.heappop(active)
            if r['exit'] > r['entry']:
                overlaps += len(active)
                heapq.heappush(active, r['exit'])
        for a, b in zip(ordered, ordered[1:]):
            if a['exit'] <= b['entry']:
                adjacent += 1
                migrations += a['thread'] != b['thread']
    return {'available_intervals': sum(map(len, actors.values())),
            'unavailable_intervals': missing, 'invalid_intervals': invalid,
            'zero_duration_intervals': zero,
            'same_actor_overlapping_pairs': overlaps,
            'nonoverlapping_adjacent_pairs': adjacent,
            'thread_changes_between_nonoverlapping_neighbors': migrations,
            'reservation_order_entry_reversals': reservation_reversals,
            'scheduler_exclusion_proved': False,
            'input_ingestion_order_proved': False}


def job_attribution(records):
    counts = Counter()
    jobs = set()
    sizes = Counter()
    for r in records:
        if 'attribution_attempted' not in r and 'attribution_valid' not in r:
            counts['unavailable_records'] += 1
            continue
        attempted, valid = r.get('attribution_attempted'), r.get('attribution_valid')
        if any(type(x) is not int or x not in (0,1) for x in (attempted,valid)) or valid > attempted:
            counts['malformed_records'] += 1
            continue
        if not attempted:
            counts['unattempted_records'] += 1
        elif not valid:
            counts['rejected_records'] += 1
        else:
            job, index, count = r.get('job'), r.get('record_index'), r.get('initial_count')
            try:
                address = int(job,16) if isinstance(job,str) else 0
            except ValueError:
                address = 0
            if (not 0 < address < 1 << 64 or type(index) is not int or
                    type(count) is not int or not 0 <= index < count <= 0x3fff):
                counts['malformed_records'] += 1
                continue
            jobs.add(address); sizes[count] += 1; counts['valid_records'] += 1
    return {**{k:counts[k] for k in ('valid_records','rejected_records','unattempted_records',
                                    'unavailable_records','malformed_records')},
            'unique_job_addresses':len(jobs), 'initial_record_count_histogram':dict(sorted(sizes.items())),
            'batch_generation_established':False}


def direct_substeps(records):
    counts = Counter(); selected = Counter(); differences = Counter()
    groups = []; previous = None
    for r in records:
        flag = r.get('frame_valid')
        if flag is None:
            counts['unavailable_records'] += 1; previous = None; continue
        if type(flag) is not int or flag not in (0,1):
            counts['malformed_records'] += 1; previous = None; continue
        if not flag:
            counts['invalid_frame_records'] += 1; previous = None; continue
        ordinal, count, outer = (r.get(k) for k in
                                ('substep_ordinal','selected_count','outer_completion_counter'))
        if (any(type(x) is not int for x in (ordinal,count,outer)) or
                not 0 <= ordinal < count < 1 << 32 or not 0 <= outer < 1 << 64 or
                type(r.get('attribution_valid')) is not int or r['attribution_valid'] != 1):
            counts['malformed_records'] += 1; previous = None; continue
        before, after = r['before'], r['after']
        if (not (before['valid'] & 1 and after['valid'] & 1) or
                any(before[k] != after[k] for k in ('runtime','main','rider'))):
            counts['identity_rejected_records'] += 1; previous = None; continue
        counts['valid_records'] += 1; selected[count] += 1
        if (before['valid'] & 4 and after['valid'] & 4 and before['request']==after['request']
                and type(before['request']) is int and 0 <= before['request'] < 1 << 32):
            differences[(before['request'] - outer) & 0xffffffff] += 1
        key=(r['actor'],before['runtime'],before['main'],before['rider'],outer)
        if previous != key: groups.append([])
        groups[-1].append((ordinal,count));previous=key
    complete = sum(len(g)==g[0][1] and all(n==g[0][1] and ordinal==i
                   for i,(ordinal,n) in enumerate(g)) for g in groups)
    return {**{k:counts[k] for k in ('valid_records','unavailable_records','invalid_frame_records',
                                    'malformed_records','identity_rejected_records')},
            'selected_count_histogram':dict(sorted(selected.items())),
            'observed_outer_groups':len(groups),'complete_ordinal_sequences':complete,
            'partial_or_nonsequential_groups':len(groups)-complete,
            'request_minus_outer_mod32_histogram':dict(sorted(differences.items())),
            'counter_semantic_equivalence_proved':False,
            'global_invocation_identity_established':False}


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
    direct = direct_substeps(records)
    return {
        'direct_substeps': direct,
        'job_attribution': job_attribution(records),
        'wrapper_intervals': interval_order(records),
        'preconsume_counter': counter_changes(records),
        'preconsume_countdown': countdown_changes(records),
        'records': len(records), 'rejected_timing_records': rejected,
        'observed_request_groups': len(groups),
        'records_per_group': dict(sorted(histogram.items())),
        'float32_subdivision_matching_groups': exact,
        'nonmatching_or_partial_groups': mismatched,
        'loss_free_export': summary.get('dropped') == 0,
        'slot_lifecycle_passed': all(summary.get(k) == 1 for k in ('installed', 'restored', 'drained')),
        'direct_native_substep_index_used': direct['valid_records'] > 0,
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
