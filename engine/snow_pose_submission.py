"""Recovered spring preparation through pose destination storage.

Evidence: CENTRAL_IMPULSE.md, Spring coefficients to submitted pose storage.
This inspection API does not apply forces or execute body notifications.
"""
import argparse
import json
from pathlib import Path
import struct
from .snow_pose_springs import pose_spring_coefficients
from .snow_pose_pair import order_pose_bodies
from .snow_pose_record import POSE_VECTOR_MASK, prepare_pose_submission


def prepare_spring_submission(source, previous_storage, mass_like, frequencies,
                              damping_ratios, *, swap_byte=0, request_byte=0,
                              vector_mask=POSE_VECTOR_MASK):
    """Update only recovered spring fields, then pack and store the record.

    Caller asserts this preparation and submission are reached in this order.
    Native intervening work, locks, object lifetime and phase timing are external.
    Source is the packed record at wrapper+0x18, not the wrapper itself.
    """
    if len(source)!=256:raise ValueError('Exact 0x100 source size required')
    records=pose_spring_coefficients(mass_like,frequencies,damping_ratios)
    prepared=bytearray(source)
    for record,flag,coeff in zip(records,(0x9c,0xb0,0xc4),(0xa8,0xbc,0xd0)):
        struct.pack_into('<I',prepared,flag,record['disabled'])
        struct.pack_into('<2f',prepared,coeff,record['stiffness'],record['damping'])
    result=prepare_pose_submission(prepared,previous_storage,vector_mask,swap_byte,request_byte)
    return dict(source=bytes(prepared),storage=result['storage'],notify=result['notify'],records=records)


def inspect(document):
    if document.get('schema')!='snow-pose-submission-v1':raise ValueError('Unsupported schema')
    if document.get('provenance') not in ('authored_synthetic','caller_supplied_observation'):
        raise ValueError('Explicit provenance required')
    if document.get('sequence')!='caller_asserted_prepare_then_submit':
        raise ValueError('Explicit sequence assertion required')
    args=dict(document['inputs'])
    pair=None
    if 'body_pair' in args:
        if 'swap_byte' in args:raise ValueError('Supply body_pair or swap_byte, not both')
        pair=order_pose_bodies(**args.pop('body_pair'))
        args['swap_byte']=int(pair['frame_swap'])
    for name in ('source','previous_storage','vector_mask'):
        if name in args:args[name]=bytes.fromhex(args[name])
    result=prepare_spring_submission(**args)
    return dict(schema=document['schema'],provenance=document['provenance'],
                source=result['source'].hex(),storage=result['storage'].hex(),
                notify=result['notify'],records=result['records'],body_pair=pair,
                limits=['No solver or notification effects executed',
                        'Caller supplies phase ordering and retained record state',
                        'No native object lookup or live mutation'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=inspect(json.loads(args.input.read_text()))
    encoded=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(encoded)
    else:print(encoded,end='')


if __name__=='__main__':main()
