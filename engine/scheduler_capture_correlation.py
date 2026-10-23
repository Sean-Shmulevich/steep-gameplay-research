"""Correlate bounded graphics main/finalizer captures, without publishing pointers.

Evidence: SCHEDULER_DELEGATES.md. Inputs are private capture envelopes containing
session (caller-verified PID/creation identity token), image_base, and JSONL rows.
Session identity is asserted by the capture controller, not verified by this
file analyzer. Guards and request equality do not pin owner lifetime or prove ABA
absence. No native execution, input, mutation, or complete-dispatch claim.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path


def _integer(value, low=0, high=2**64-1):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('invalid integer')
    return value


def _pointer(value):
    if not isinstance(value, str) or not value or len(value) > 18:
        raise ValueError('invalid pointer encoding')
    return _integer(int(value, 16))


def correlate_graphics_captures(main, finalizer):
    """Envelope rows contain one summary followed by at most 1024 records.

    Invalid/changing request observations and duplicate keys are reported, never
    guessed into pairs. Independent window edges may leave unmatched records.
    Timestamps establish observed order only within the asserted common session.
    """
    session = main.get('session')
    if not isinstance(session, str) or not session or session != finalizer.get('session'):
        raise ValueError('matching caller-verified session identity required')
    base = _integer(main.get('image_base'), 0x10000)
    if finalizer.get('image_base') != base:
        raise ValueError('image bases differ')
    captures = []; windows = []; owner = frequency = None
    for envelope, abi, site, is_final in ((main, 3, 0x65b223, False),
                                        (finalizer, 1, 0x11e2dff, True)):
        rows = envelope.get('rows')
        if not isinstance(rows, list) or not 1 <= len(rows) <= 1025:
            raise ValueError('invalid bounded capture')
        summary = rows[0]
        if summary.get('kind') != 'summary' or summary.get('record_abi') != abi:
            raise ValueError('unsupported capture ABI')
        if is_final and summary.get('probe') != 'finalizer':
            raise ValueError('finalizer probe identity missing')
        if any(summary.get(k) != 1 for k in ('compatible', 'configured', 'installed', 'restored', 'drained')):
            raise ValueError('capture lifecycle incomplete')
        if _integer(summary.get('used'), 0, 1024) != len(rows)-1 or summary.get('dropped') != 0:
            raise ValueError('incomplete or dropped records')
        current_owner = _pointer(summary.get('owner'))
        current_frequency = _integer(summary.get('qpf'), 1)
        if owner is not None and (owner != current_owner or frequency != current_frequency):
            raise ValueError('owner or clock domain differs')
        owner, frequency = current_owner, current_frequency
        keyed = defaultdict(list); rejected = 0
        for i, record in enumerate(rows[1:]):
            if record.get('kind') != 'record' or record.get('index') != i:
                raise ValueError('record order/identity malformed')
            if (_pointer(record.get('storage')) != (0 if is_final else owner+0x3b0) or
                    _pointer(record.get('receiver')) != (owner+0x218 if is_final else owner) or
                    _pointer(record.get('caller')) != base+site):
                raise ValueError('record binding/caller differs')
            entry = _integer(record.get('entry')); end = _integer(record.get('exit'))
            _integer(record.get('thread'))
            if end < entry:
                raise ValueError('reversed timestamps')
            before, after = record['before'], record['after']
            values = []
            for state in (before, after):
                _integer(state.get('valid'), 0, 1)
                for field in ('executions', 'state', 'started', 'requested', 'holds'):
                    _integer(state.get(field), 0, 2**32-1)
                _integer(state.get('outstanding'), -2**31, 2**31-1)
                for field in ('usage', 'selector'):
                    _integer(state.get(field), 0, 255)
                values.extend((state['started'], state['requested']))
            if before['valid'] != 1 or after['valid'] != 1 or len(set(values)) != 1:
                rejected += 1;continue
            keyed[values[0]].append(record)
        captures.append((keyed, rejected))
        windows.append((min(r['entry'] for r in rows[1:]), max(r['exit'] for r in rows[1:]))
                       if len(rows) > 1 else None)
    a, b = captures[0][0], captures[1][0]
    ambiguous = sorted(k for k in a.keys() | b.keys() if len(a[k]) > 1 or len(b[k]) > 1)
    pairs = []; unmatched_main = unmatched_finalizer = 0
    for request in sorted(a.keys() | b.keys()):
        if request in ambiguous:
            continue
        if not a[request]:
            unmatched_finalizer += 1;continue
        if not b[request]:
            unmatched_main += 1;continue
        m, f = a[request][0], b[request][0]
        signature = lambda s: (s['executions'], s['outstanding'], s['state'])
        pairs.append(dict(request=request, observed_order=m['exit'] <= f['entry'],
            same_thread=m['thread'] == f['thread'],
            gap_ticks=f['entry']-m['exit'],
            accounting_matches=(signature(m['before']) == (1, 1, 2) and
                signature(m['after']) == (1, 1, 2) and signature(f['before']) == (0, 1, 2)
                and signature(f['after']) == (0, 1, 0))))
    overlap = (all(w is not None for w in windows) and
               max(w[0] for w in windows) <= min(w[1] for w in windows))
    return dict(schema='graphics-phase-correlation-v1', pairs=pairs, pair_count=len(pairs),
        observed_capture_windows_overlap=bool(overlap),
        rejected_main=captures[0][1], rejected_finalizer=captures[1][1],
        ambiguous_requests=ambiguous, unmatched_main=unmatched_main,
        unmatched_finalizer=unmatched_finalizer, clock_frequency=frequency,
        session_identity_source='caller assertion', atomic_snapshot=False,
        outstanding_decrement_observed=False, native_mutation_authorized=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('main_capture', type=Path)
    parser.add_argument('finalizer_capture', type=Path)
    args = parser.parse_args()
    result = correlate_graphics_captures(json.loads(args.main_capture.read_text()),
                                        json.loads(args.finalizer_capture.read_text()))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
