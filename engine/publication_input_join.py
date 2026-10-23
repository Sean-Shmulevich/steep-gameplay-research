"""Authored temporal/value comparison, not a proof of an ingestion call.

Caller selects and qualifies identities, supplies records from one clock domain,
and resolves the X-sign gate. No nearest-value search or float tolerance is used.
"""
import bisect
from collections import Counter


def compare_publications(events, updates, *, flip_x):
    """Compare the latest completed parent sample to each bracketed update.

    Records contain entry, exit, valid and bits (four uint32 lanes). Events must
    not overlap. Updates are accepted only within the gap before the next event,
    so an absent tail cannot silently count as a valid publication interval.
    Invalid latest samples are never replaced with older matching values.
    """
    if type(flip_x) is not bool:
        raise ValueError('flip_x must be an explicitly resolved boolean')
    def checked(records):
        result = []
        for r in records:
            if any(type(r[k]) is not int or not 0 <= r[k] < 1 << 64 for k in ('entry', 'exit')):
                raise ValueError('timestamps must be uint64')
            if r['exit'] < r['entry'] or type(r['valid']) is not bool:
                raise ValueError('invalid interval or validity flag')
            bits = tuple(r['bits'])
            if len(bits) != 4 or any(type(x) is not int or not 0 <= x < 1 << 32 for x in bits):
                raise ValueError('expected four uint32 lanes')
            result.append(dict(entry=r['entry'], exit=r['exit'], valid=r['valid'], bits=bits))
        return sorted(result, key=lambda r: r['entry'])
    sources, targets = checked(events), checked(updates)
    if any(a['exit'] > b['entry'] or a['entry'] == b['entry'] for a, b in zip(sources, sources[1:])):
        raise ValueError('overlapping or tied parent events leave ordering ambiguous')
    ends = [r['exit'] for r in sources]
    counts = Counter()
    comparisons = []
    for target in targets:
        i = bisect.bisect_right(ends, target['entry']) - 1
        if not target['valid']:
            verdict = 'invalid_target'
        elif i < 0:
            verdict = 'no_completed_parent'
        elif i + 1 >= len(sources):
            verdict = 'unbounded_tail'
        elif sources[i + 1]['entry'] < target['exit']:
            verdict = 'overlapping_next_parent'
        elif not sources[i]['valid']:
            verdict = 'invalid_latest_parent'
        else:
            expected = list(sources[i]['bits'])
            if flip_x:
                expected[0] ^= 0x80000000
            verdict = 'match' if tuple(expected) == target['bits'] else 'mismatch'
        counts[verdict] += 1
        comparisons.append(dict(parent_index=i if i >= 0 else None, verdict=verdict))
    return dict(counts=dict(counts), comparisons=comparisons,
                proves_copy_execution=False, sign_gate_supplied=flip_x)


def delivery_window_coverage(intervals, *, key_down, key_up):
    """Check sampled interval coverage against delivery reports in one clock.

    This only checks observation-window coverage, never game input acceptance.
    Both reports must lie inside the measured span, with an interval intersecting
    the hold. It does not assert continuous sampling between recorded intervals.
    """
    if any(type(x) is not int or not 0 <= x < 1 << 64 for x in (key_down, key_up)) or key_down > key_up:
        raise ValueError('invalid delivery interval')
    spans = []
    for start, end in intervals:
        if any(type(x) is not int or not 0 <= x < 1 << 64 for x in (start, end)) or end < start:
            raise ValueError('invalid observation interval')
        spans.append((start, end))
    if not spans:
        return dict(covered=False, key_down_inside=False, key_up_inside=False, intersecting_intervals=0)
    first = min(a for a, _ in spans)
    last = max(b for _, b in spans)
    down, up = first <= key_down <= last, first <= key_up <= last
    count = sum(start < key_up and end > key_down for start, end in spans)
    return dict(covered=down and up and count > 0, key_down_inside=down,
                key_up_inside=up, intersecting_intervals=count)
