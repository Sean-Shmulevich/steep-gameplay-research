"""JSON inspection API for explicit cache-publication and vector-refresh events.

No device access or native process. Event ordering and resolved gates are supplied
by the caller; event indices are harness labels, never native sample generations.
"""
import copy
import argparse
import hashlib
import json
from pathlib import Path
import struct
from .action_cache_exchange import CACHE_SPAN
from .action_cache_directions import publish_derived_and_stamp
from .action_sample import f32
from .action_processor import initial_state, process_default
from .vector_action_refresh import refresh_vector_action


def inspect_timeline(plan):
    if not isinstance(plan, dict) or set(plan) != {'events'}:
        raise ValueError('plan requires only events')
    if not isinstance(plan['events'], list) or len(plan['events']) > 1000:
        raise ValueError('events must be a list of at most 1000 items')
    root, action = bytes(CACHE_SPAN), bytes(192)
    processor_state = initial_state()
    observations = []
    for index, event in enumerate(plan['events']):
        if not isinstance(event, dict):
            raise ValueError('each event must be an object')
        kind = event.get('event')
        diagnostics = None
        if kind == 'publish':
            if set(event) != {'event', 'vectors', 'scalars', 'now'}:
                raise ValueError('publish requires vectors, scalars and opaque uint64 now')
            vectors, scalars = event['vectors'], event['scalars']
            if not isinstance(vectors, list) or len(vectors) != 2 or any(not isinstance(v, list) or len(v) != 4 for v in vectors):
                raise ValueError('two four-lane vectors required')
            if not isinstance(scalars, list) or len(scalars) != 32:
                raise ValueError('32 scalar channels required')
            selected = bytearray(CACHE_SPAN)
            struct.pack_into('<8f', selected, 0x1f0, *(f32(v) for row in vectors for v in row))
            struct.pack_into('<32f', selected, 0x168, *(f32(v) for v in scalars))
            root = publish_derived_and_stamp(root, bytes(selected), event['now'])
        elif kind == 'refresh':
            required = {'event', 'source_kind', 'lane_mode', 'owner_suppressed',
                        'configuration_available', 'ownership_blocked', 'cache_masked', 'processor'}
            if set(event) != required:
                raise ValueError('refresh requires explicit source, lane, four boolean gates and processor')
            for gate in ('owner_suppressed', 'configuration_available', 'ownership_blocked', 'cache_masked'):
                if type(event[gate]) is not bool:
                    raise ValueError(gate+' must be boolean')
            for selector in ('source_kind', 'lane_mode'):
                if type(event[selector]) is not int or not 0 <= event[selector] < 1 << 32:
                    raise ValueError(selector+' must be uint32')
            if event['processor'] not in ('bypass', 'default'):
                raise ValueError('processor must explicitly select bypass or default')
            def process(raw):
                nonlocal processor_state
                evaluated = process_default(list(struct.unpack('<4f', raw)), processor_state)
                processor_state = evaluated['state']
                return struct.pack('<4f', *evaluated['output'])
            def read_vector(channel):
                return bytes(16) if event['cache_masked'] else root[0x1f0+channel*16:0x200+channel*16]
            def read_scalar(channel):
                return bytes(4) if event['cache_masked'] else root[0x168+channel*4:0x16c+channel*4]
            result = refresh_vector_action(action, owner_suppressed=event['owner_suppressed'],
                configuration_available=event['configuration_available'], kind=event['source_kind'],
                lane_mode=event['lane_mode'], ownership_blocked=lambda *_: event['ownership_blocked'],
                read_vector=read_vector, read_scalar=read_scalar,
                processing_enabled=event['processor'] == 'default', process=process)
            action = result.pop('snapshot')
            diagnostics = result
        else:
            raise ValueError('unknown event type')
        observations.append(dict(event_index=index, event=kind,
            cache_clock=struct.unpack_from('<Q', root, 0x58)[0],
            derived_press_stamps=list(struct.unpack_from('<8Q', root, 0x7d8)),
            raw=list(struct.unpack_from('<4f', action, 0x50)),
            sample=list(struct.unpack_from('<4f', action, 0x60)),
            direction=list(struct.unpack_from('<4f', action, 0x70)),
            magnitude=struct.unpack_from('<f', action, 0x80)[0],
            status=action[0x30], diagnostics=diagnostics,
            processor_state=copy.deepcopy(processor_state)))
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return dict(schema_version=1, input_sha256=digest, observations=observations,
        scope='Synthetic zero-initialized caches/action, caller-ordered events and resolved gates; explicit bypass or default-copy processor. No device polling, native scheduling or game access.',
        sample_generation_established=False,
        direction_policy='Derived scalar reciprocal seed with recovered refinement; not native RSQRT seed parity')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = inspect_timeline(json.loads(args.input.read_text()))
    payload = json.dumps(result, indent=2, allow_nan=False)+'\n'
    if args.output:
        args.output.write_text(payload)
    else:
        print(payload, end='')


if __name__ == '__main__': main()
