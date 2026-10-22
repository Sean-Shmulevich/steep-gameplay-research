"""Aggregate optional private motion observations without exporting their values.

Equality is raw-bit equality, not input freshness or ingestion-call evidence.
Adjacent comparisons require ordered, nonoverlapping records from one actor;
frame counters identify observed boundaries, not a global invocation identity.
"""
from collections import Counter

ARRAYS = {'latches': 3, 'ingested_bits': 8, 'current_input_bits': 8,
          'nonzero_counts': 2, 'baseline_bits': 12}
POINTERS = ('motion', 'current', 'pending', 'state_current', 'state_pending',
            'child_current', 'child_pending')
SCALARS = ('current_mode', 'pending_mode', 'lock_word', 'lock_owner', 'lock_depth',
           'query_depth', 'state_mode', 'state_pending_mode', 'child_mode',
           'child_pending_mode', 'state_observed', 'child_observed', 'enabled',
           'immediate', 'pending_service')
FIELDS = POINTERS + SCALARS + tuple(ARRAYS)


def uint(v, bits=32):
    return type(v) is int and 0 <= v < 1 << bits


def valid_sample(s):
    if not isinstance(s, dict):
        return False
    for key in POINTERS:
        v = s.get(key)
        if not isinstance(v, str) or not v or len(v) > 16:
            return False
        try:
            if not uint(int(v, 16), 64):
                return False
        except ValueError:
            return False
    if any(not uint(s.get(k)) for k in SCALARS):
        return False
    for k, n in ARRAYS.items():
        v = s.get(k)
        if not isinstance(v, list) or len(v) != n or any(not uint(x, 8 if k == 'latches' else 32) for x in v):
            return False
    return True


def changes(a, b):
    return [k for k in FIELDS if (int(a[k], 16) != int(b[k], 16) if k in POINTERS else a[k] != b[k])]


def analyze_motion(records):
    counts = Counter()
    within, same, boundary = Counter(), Counter(), Counter()
    previous = None
    for r in records:
        if 'motion_attempted' not in r:
            counts['unavailable_records'] += 1
            previous = None
            continue
        flags = [r.get(k) for k in ('motion_attempted', 'motion_before_valid', 'motion_after_valid')]
        if any(type(v) is not int or v not in (0, 1) for v in flags) or (not flags[0] and any(flags[1:])):
            counts['malformed_records'] += 1
            previous = None
            continue
        if not flags[0]:
            counts['disabled_records'] += 1
            previous = None
            continue
        counts['attempted_records'] += 1
        before, after = r.get('motion_before'), r.get('motion_after')
        if any(flag and not valid_sample(s) for flag, s in zip(flags[1:], (before, after))):
            counts['malformed_records'] += 1
            previous = None
            continue
        counts['before_rejected'] += not flags[1]
        counts['after_rejected'] += not flags[2]
        if not all(flags[1:]):
            previous = None
            continue
        counts['valid_pairs'] += 1
        within.update(changes(before, after))
        if previous is not None:
            p = previous
            ordered = all(uint(x, 64) for x in (p.get('entry'), p.get('exit'), r.get('entry'), r.get('exit')))
            ordered = ordered and p['entry'] < p['exit'] <= r['entry'] < r['exit']
            frames = all(x.get('frame_valid') == 1 and x.get('attribution_valid') == 1
                         and uint(x.get('outer_completion_counter'), 64)
                         and uint(x.get('substep_ordinal')) and uint(x.get('selected_count'))
                         and 0 <= x['substep_ordinal'] < x['selected_count'] for x in (p, r))
            owner = p.get('actor') is not None and p.get('actor') == r.get('actor')
            owner = owner and int(p['motion_after']['motion'], 16) == int(before['motion'], 16)
            if ordered and frames and owner:
                if p['outer_completion_counter'] == r['outer_completion_counter']:
                    if p['selected_count'] == r['selected_count'] and r['substep_ordinal'] == p['substep_ordinal'] + 1:
                        counts['adjacent_same_batch_pairs'] += 1
                        same.update(changes(p['motion_after'], before))
                    else:
                        counts['nonsequential_pairs'] += 1
                else:
                    counts['observed_boundary_pairs'] += 1
                    boundary.update(changes(p['motion_after'], before))
            else:
                counts['unqualified_neighbor_pairs'] += 1
        previous = r
    return {'counts': dict(counts), 'within_update_changed_fields': dict(within),
            'same_batch_gap_changed_fields': dict(same),
            'observed_boundary_changed_fields': dict(boundary),
            'ingestion_execution_proved': False, 'atomic_snapshot_proved': False,
            'producer_generation_established': False}
