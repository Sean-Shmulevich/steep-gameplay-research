"""Inspection of recovered contact consumers with explicitly supplied state.

Contract: CENTRAL_IMPULSE.md, Runnable contact-output inspection. Record identity
and freshness across submission/reporting are caller assumptions, not measured.
"""
import argparse
from copy import deepcopy
import json
from math import sqrt
from pathlib import Path
from .snow_post_pending import summed_submissions
from .snow_contact_reporting import report_contact, accumulate_contact_bucket, finalize_contact_bucket

BOUNDARIES = [
    'Caller supplies records, gates, frame, initial report state and initial buckets',
    'Phase continuity is supplied by caller; native freshness and intervening writes unproved',
    'Submissions are vectors, not applied body motion or solver results',
    'Mathematical reciprocal sqrt seed substitutes for hardware approximate instruction',
    'No native allocation, scheduler, aggregate consumers or landing classifier',
]


def inspect(document):
    if document.get('schema') != 'snow-contact-bench-v1':
        raise ValueError('snow-contact-bench-v1 schema required')
    if document.get('provenance') not in ('authored_synthetic', 'caller_supplied_observation'):
        raise ValueError('explicit provenance required')
    data=deepcopy(document)
    records=data['records']
    continuity=data.get('record_continuity')
    if continuity == 'caller_asserted_unchanged':
        if 'reporting_records' in data:
            raise ValueError('Unchanged mode cannot also supply separate reporting records')
        reporting_records=records
    elif continuity == 'separate_phase_snapshots':
        reporting_records=data['reporting_records']
    else:
        raise ValueError('Explicit record_continuity required')
    if len(data['buckets']) != 2:
        raise ValueError('two supplied initial buckets required')
    impulses=summed_submissions(records,data['gate_one'],data['gate_other'],data['elapsed'])
    report=data['report_state'];buckets=data['buckets'];events=[]
    for i,record in enumerate(reporting_records):
        gate=data['gate_one'] if record['kind']==1 else data['gate_other']
        prior_reports=len(report['records']);prior_counts=[b['count'] for b in buckets]
        report=report_contact(report,record,gate)
        buckets=accumulate_contact_bucket(buckets,record,data['frame_columns'])
        events.append(dict(record=i,reported=len(report['records'])!=prior_reports,
                           groups_changed=[j for j,b in enumerate(buckets) if b['count']!=prior_counts[j]]))
    final=[finalize_contact_bucket(b,data['fallback_point'],lambda x:1/sqrt(x)) for b in buckets]
    return dict(schema='snow-contact-result-v1',provenance=data['provenance'],record_continuity=continuity,
                impulse_submissions=impulses,report_state=report,accumulated_buckets=buckets,
                finalized_buckets=final,record_events=events,boundaries=BOUNDARIES)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=inspect(json.loads(args.input.read_text()))
    text=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(text)
    else:print(text,end='')


if __name__ == '__main__':
    main()
