"""Inspect the version-94 second-stage live-replay container, not a ghost file.

Evidence: docs/reconstruction/LIVE_REPLAY_LEADS.md. Public output uses ordinal
channel names; no unit, body identity or animation semantics are inferred.
"""
import argparse
import json
import math
from pathlib import Path
import struct
from .replay_columns import decode_columns
from .replay_state import decode_state
from .replay_spatial import f32


def decode_record(payload, *, version, rsqrt_seed):
    if type(version) is not int or version != 94:
        raise ValueError('Only record version 94 is supported')
    if not isinstance(payload, (bytes, bytearray)) or len(payload) < 282:
        raise ValueError('Version-94 record requires 282 bytes')
    words = list(struct.unpack_from('<3I', payload, 7))
    raw_scalars = struct.unpack_from('<2H', payload, 19)
    return {'metadata': {'tags':list(payload[:4]), 'flag_bytes':list(payload[4:7]),
                         'raw_words':words,
                         'scalars':[f32(raw_scalars[0]/10),f32(raw_scalars[1]/100)]},
            'state':decode_state(payload[23:282],version=version,rsqrt_seed=rsqrt_seed),
            'consumed':282}


def inspect_stage(payload, *, supplied_version, rsqrt_seed, max_records=4096,
                  max_output=16*1024*1024):
    """Parse one stage; return its consumed boundary and record tail lengths.

    Allocation and count limits are authored guards. Width extensions are counted
    but not interpreted. Zero-record and non-94 branches are explicitly unsupported.
    """
    if type(supplied_version) is not int or not 0 <= supplied_version <= 0xffffffff:
        raise ValueError('Unsigned supplied version required')
    if type(max_records) is not int or max_records < 1:
        raise ValueError('Positive record bound required')
    if not isinstance(payload,(bytes,bytearray)) or len(payload)<16:
        raise ValueError('Truncated stage header')
    embedded,unknown,count,size=struct.unpack_from('<4I',payload)
    effective=embedded if supplied_version>=45 else supplied_version
    if effective!=94:
        raise ValueError('Only effective version 94 is supported')
    if not 1<=count<=max_records:
        raise ValueError('Record count outside supported bound')
    if size>len(payload)-16:
        raise ValueError('Truncated declared compressed block')
    columns=decode_columns(payload[16:16+size],count,max_output=max_output)
    width=columns['record_width']
    if width<282:
        raise ValueError('Record width smaller than version-94 schema')
    records=[]
    for index in range(count):
        record=decode_record(columns['data'][index*width:(index+1)*width],
                             version=effective,rsqrt_seed=rsqrt_seed)
        record['uninterpreted_tail_bytes']=width-record['consumed']
        records.append(record)
    return {'effective_version':effective,'header_raw_word':unknown,
            'record_width':width,'record_count':count,'records':records,
            'compressed_bytes_consumed':columns['consumed'],
            'compressed_trailing_bytes':size-columns['consumed'],
            'consumed':16+size}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--supplied-version',type=int,required=True)
    parser.add_argument('--normalization',choices=['authored-exact-sqrt'],required=True)
    parser.add_argument('--max-records',type=int,default=4096)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    # Bound the read itself, not only the decompressed allocation.
    with args.input.open('rb') as source:
        payload=source.read(32*1024*1024+1)
    if len(payload)>32*1024*1024:
        parser.error('Input exceeds 32 MiB inspection limit')
    try:
        report=inspect_stage(payload,supplied_version=args.supplied_version,
                             rsqrt_seed=lambda s:1/math.sqrt(s),max_records=args.max_records)
    except ValueError as error:
        parser.error(str(error))
    report['normalization']='authored exact sqrt seed; not hardware-exact RSQRTPS'
    report['input_trailing_bytes']=len(payload)-report['consumed']
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
