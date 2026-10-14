"""Decode defined animation packet bytes and pair debugger observations.

Designed trace analysis, not a recovered scheduler or an execution injector.
Debugger wall time is deliberately not presented as callback duration.
"""
import math
import struct


def decode_packet(data):
    if type(data) is not bytes or len(data) != 15:
        raise ValueError('expected the 15 defined packet bytes')
    bits = struct.unpack_from('<I', data, 8)[0]
    interval = struct.unpack_from('<f', data, 8)[0]
    return dict(interval_bits=bits, interval=interval if math.isfinite(interval) else None,
                interval_finite=math.isfinite(interval), status_bytes=list(data[12:15]))


def pair_calls(records):
    if type(records) is not list or len(records) > 10000:
        raise ValueError('expected at most 10000 trace records')
    pending, pairs, unmatched = {}, [], []
    last_sequence = None

    def discard(thread=None, reason='trace_interrupted'):
        for key in list(pending):
            if thread is None or key == thread:
                unmatched.extend(dict(sequence=r['sequence'], reason=reason) for r in pending.pop(key))

    for row in records:
        if type(row) is not dict:
            raise ValueError('trace row must be an object')
        kind = row.get('kind')
        if kind in ('error', 'unexpected_stop', 'cleanup_error', 'loss', 'window_end'):
            discard(reason=kind)
            continue
        if kind != 'hit':
            continue
        sequence, thread = row.get('sequence'), row.get('thread')
        if type(sequence) is not int or sequence <= 0 or type(thread) is not int or thread <= 0:
            raise ValueError('invalid event sequence or thread')
        if last_sequence is not None and sequence <= last_sequence:
            raise ValueError('event sequence must increase')
        if last_sequence is not None and sequence != last_sequence + 1:
            discard(reason='sequence_gap')
        last_sequence = sequence
        event = row.get('event')
        if event not in ('call_before', 'call_after'):
            discard(reason='unexpected_event')
            continue
        try:
            component = int(row['registers']['rdi'], 16)
            stack = int(row['registers']['rsp'], 16)
            data = bytes.fromhex(row['packet_hex'])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('missing event identity or packet') from error
        if not 0 < component < 2**64 or not 0 < stack < 2**64:
            raise ValueError('invalid component or stack identity')
        packet = decode_packet(data)
        item = dict(sequence=sequence, thread=thread, component=component, stack=stack, packet=packet)
        frames = pending.setdefault(thread, [])
        if event == 'call_before':
            if any(r['component'] == component and r['stack'] == stack for r in frames):
                discard(thread, 'duplicate_entry')
                unmatched.append(dict(sequence=sequence, reason='duplicate_entry'))
            else:
                frames.append(item)
        elif frames and (frames[-1]['component'], frames[-1]['stack']) == (component, stack):
            before = frames.pop()
            pairs.append(dict(thread=thread, component=component, stack=stack,
                              before_sequence=before['sequence'], after_sequence=sequence,
                              before=before['packet'], after=packet))
        else:
            discard(thread, 'return_identity_mismatch')
            unmatched.append(dict(sequence=sequence, reason='unmatched_return'))
    discard(reason='capture_ended')
    return dict(pairs=pairs, unmatched=unmatched, timing_cost_established=False,
                scheduler_request_identity_established=False,
                scope='Matched observed before/after call sites; not a whole-component or physics-step trace.')


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('events', help='Private JSONL observation receipt')
    args = parser.parse_args()
    rows = []
    with open(args.events, encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                rows.append(json.loads(line))
                if len(rows) > 10000:
                    raise ValueError('trace exceeds 10000 records')
    print(json.dumps(pair_calls(rows), indent=2, allow_nan=False))
