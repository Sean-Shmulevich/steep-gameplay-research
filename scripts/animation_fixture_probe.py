#!/usr/bin/env python3
"""Read-only protocol checks against an already running synthetic Snow host."""
import argparse
import json
from snow_host_client import SnowHostClient


def probe(client):
    hello = client.call('host.hello')
    if hello.get('adapter') != 'fixture-simulated':
        raise ValueError('requires fixture-simulated adapter; refusing game host')
    observed = client.call('animation.get_channel', key=10)
    missing = client.call('animation.get_channel', key=4294967295)
    checks = {
        'synthetic_values': observed.get('found') is True
        and observed.get('vector') == [1, 2, 3, 0]
        and observed.get('rotation') == [0, 0, 0, 1],
        'explicit_limits': observed.get('guards_matched') is True and all(
            observed.get(k) is False for k in ('atomic_snapshot', 'lifetime_pinned',
                'animation_completion_established', 'suitable_for_animation_writes')),
        'provider_conversion': observed.get('conversion_direct') is True
        and observed.get('provider_vector') == observed.get('vector')
        and observed.get('provider_rotation') == observed.get('rotation')
        and observed.get('parent_rotation') == [0, 0, 0, 1]
        and observed.get('record_index') == 0
        and observed.get('coordinate_space_semantics') == 'native_provider_conversion_only',
        'owner_observation': observed.get('owner_accessor_present') is False
        and observed.get('owner_reader_word') == 0
        and observed.get('owner_transform_freshness_established') is False
        and observed.get('owner_matrix') == [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],
        'missing_key': missing.get('found') is False and 'vector' not in missing
        and 'rotation' not in missing,
    }
    for label, params in [('absent', {}), ('negative', {'key': -1}),
                          ('overflow', {'key': 4294967296})]:
        result = client.request('animation.get_channel', **params)
        checks[label] = result.get('status') == 'failed' and result.get('result', {}).get('error') == 'invalid_channel_key'
    return {'schema': 'animation-host-fixture-v1', 'evidence': 'synthetic protocol only',
            'checks': checks, 'ok': all(checks.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=47117)
    args = parser.parse_args()
    with SnowHostClient(port=args.port) as client:
        result = probe(client)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ok'] else 1)
