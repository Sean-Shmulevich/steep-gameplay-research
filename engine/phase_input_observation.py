"""Authored correlation of request intervals with two OS input delivery reports.

Caller supplies verified acquisition/clock provenance. This code cannot establish
that provenance or game input ingestion. Report timestamps occur after the input
API call; they do not bound its start or the game's consumption of the key.
See SCHEDULER_DELEGATES.md, Timed input observation.
"""

def correlate_input_reports(receipts, delivery, *, request_domain, input_domain):
    def uint(value, positive=False):
        return type(value) is int and int(positive) <= value < 2**64

    def domain(value):
        if not isinstance(value, dict) or any(
            not isinstance(value.get(key), str) or not value[key]
            for key in ('session_id', 'clock_id')):
            raise ValueError('session and clock identifiers required')
        if not uint(value.get('ticks_per_second'), True):
            raise ValueError('positive uint64 clock frequency required')
        return tuple(value[k] for k in ('session_id', 'clock_id', 'ticks_per_second'))

    if domain(request_domain) != domain(input_domain):
        raise ValueError('capture sessions and clocks must match')
    delivery, receipts = list(delivery), list(receipts)
    if len(delivery) != 2:
        raise ValueError('exactly one down report and one up report required')
    for index, event in enumerate(delivery):
        if (not isinstance(event, dict) or event.get('kind') != 'key_delivery' or
            event.get('key_up') is not bool(index) or
            type(event.get('api_reported_sent')) is not int or event['api_reported_sent'] != 1 or
            not uint(event.get('qpc_ticks')) or
            not uint(event.get('pid'), True) or event['pid'] > 0xffffffff or
            any(not isinstance(event.get(k), str) or not event[k] for k in ('creation_filetime', 'hwnd')) or
            event.get('mode') not in ('sendinput', 'postmessage') or
            type(event.get('qpc_frequency')) is not int or
            event['qpc_frequency'] != request_domain['ticks_per_second'] or
            type(event.get('scan_raw')) is not int or not 1 <= event['scan_raw'] <= 255):
            raise ValueError('invalid or failed delivery report')
    for key in ('pid', 'creation_filetime', 'hwnd', 'scan_raw', 'mode'):
        if key not in delivery[0] or delivery[0][key] != delivery[1].get(key):
            raise ValueError('delivery target/key/mode changed')
    down, up = [event['qpc_ticks'] for event in delivery]
    if down >= up:
        raise ValueError('release report must follow down report')
    groups = {key: [] for key in ('before_down_report', 'inside_reported_hold',
                                  'after_up_report', 'overlaps_report_boundary')}
    for index, receipt in enumerate(receipts):
        if (not isinstance(receipt, dict) or not uint(receipt.get('id'), True) or
            type(receipt.get('outcome')) is not int or receipt['outcome'] != 1 or any(
            not uint(receipt.get(key)) for key in ('entry', 'exit'))):
            raise ValueError('invalid request interval')
        start, end = receipt['entry'], receipt['exit']
        if start > end:
            raise ValueError('request exit precedes entry')
        group = ('before_down_report' if end < down else 'after_up_report' if start > up
                 else 'inside_reported_hold' if down < start and end < up
                 else 'overlaps_report_boundary')
        groups[group].append(dict(index=index, request_id=receipt['id']))
    return dict(groups=groups, input_api_reports_accepted=True,
                report_interval_ticks=up-down,
                coverage_on_both_sides=bool(groups['before_down_report'] and groups['after_up_report']),
                ingestion_proved=False, causal_response_proved=False,
                exact_input_latency_proved=False, provenance_verified_by_analyzer=False)


def main():
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='JSON with receipts, delivery, request_domain and input_domain')
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    print(json.dumps(correlate_input_reports(**data), indent=2))


if __name__ == '__main__':
    main()
