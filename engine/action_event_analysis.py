"""Authored analysis of evaluator intervals, not recovered scheduler policy.

Input records use one clock domain. A caller supplies a candidate batch size;
matching order supports a motif, not an enclosing job or causal dependency.
No action addresses are returned in the summary.
"""
import argparse
import csv
import heapq
import json
import statistics


def analyze_action_events(records, *, batch_size, frequency, dropped=0):
    if type(batch_size) is not int or batch_size <= 0:
        raise ValueError('batch_size must be positive')
    if type(frequency) is not int or frequency <= 0:
        raise ValueError('frequency must be positive')
    if type(dropped) is not int or dropped < 0:
        raise ValueError('dropped must be nonnegative')
    rows = []
    for record in records:
        row = {}
        for name in ('action', 'thread', 'entry_qpc', 'exit_qpc'):
            value = record[name]
            if type(value) is not int or not 0 <= value < 1 << 64:
                raise ValueError('record fields must be uint64 integers')
            row[name] = value
        if row['exit_qpc'] < row['entry_qpc']:
            raise ValueError('negative interval')
        rows.append(row)
    inversions = sum(b['entry_qpc'] < a['entry_qpc'] for a, b in zip(rows, rows[1:]))
    rows.sort(key=lambda row: row['entry_qpc'])
    ties = sum(a['entry_qpc'] == b['entry_qpc'] for a, b in zip(rows, rows[1:]))
    pattern = [row['action'] for row in rows[:batch_size]]
    mismatches = sum(row['action'] != pattern[i % batch_size] for i, row in enumerate(rows))
    full = len(rows) // batch_size
    batches = [rows[i * batch_size:(i + 1) * batch_size] for i in range(full)]
    batch_threads = [batch[0]['thread'] if len({r['thread'] for r in batch}) == 1 else None for batch in batches]
    changes = sum(a is not None and b is not None and a != b for a, b in zip(batch_threads, batch_threads[1:]))
    ends = []
    overlap_entries = peak = 0
    for row in rows:
        start, end = row['entry_qpc'], row['exit_qpc']
        while ends and ends[0] <= start:
            heapq.heappop(ends)
        # A zero-width measured interval supplies no positive overlap evidence.
        if end > start:
            overlap_entries += bool(ends)
            heapq.heappush(ends, end)
            peak = max(peak, len(ends))
    gaps = [(b[0]['entry_qpc'] - a[0]['entry_qpc']) / frequency for a, b in zip(batches, batches[1:])]
    return dict(records=len(rows), dropped=dropped, no_reported_drops=dropped == 0,
        distinct_actions=len({r['action'] for r in rows}), distinct_threads=len({r['thread'] for r in rows}),
        batch_size_hypothesis=batch_size, complete_batches=full, trailing_records=len(rows) % batch_size,
        motif_has_distinct_actions=len(pattern) == batch_size and len(set(pattern)) == batch_size,
        motif_mismatches=mismatches, tied_entry_timestamps=ties, reservation_order_inversions=inversions,
        motif_order_unambiguous=bool(full) and ties == 0,
        single_thread_batches=sum(t is not None for t in batch_threads), batch_thread_changes=changes,
        entries_overlapping_previous_intervals=overlap_entries, peak_positive_width_intervals=peak,
        batch_start_gap_seconds=None if not gaps else dict(min=min(gaps), median=statistics.median(gaps), max=max(gaps)),
        proves_job_identity=False, proves_physics_order=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    parser.add_argument('--batch-size', type=int, required=True)
    parser.add_argument('--frequency', type=int, required=True)
    parser.add_argument('--dropped', type=int, default=0)
    args = parser.parse_args()
    with open(args.csv, newline='') as source:
        rows = [{k: int(v) for k, v in row.items()} for row in csv.DictReader(source)]
    print(json.dumps(analyze_action_events(rows, batch_size=args.batch_size,
        frequency=args.frequency, dropped=args.dropped), indent=2))


if __name__ == '__main__':
    main()
