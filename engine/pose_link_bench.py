"""Offline JSON inspection of one recovered link record-group update.

Evidence: CENTRAL_IMPULSE.md, Runnable link-payload inspection.
No game files, live pointers, native allocation or solver effects are required.
"""
import argparse
import json
import math
from pathlib import Path
import struct
from reference.central_impulse import f32
from .pose_link_pipeline import paired_entry_flag,process_pose_link_record_group


def inspect(document):
    if document.get('schema')!='pose-link-update-v1':raise ValueError('Unsupported schema')
    if document.get('provenance') not in ('authored_synthetic','caller_supplied_observation'):
        raise ValueError('Explicit provenance required')
    if document.get('sequence')!='reached_record_group':raise ValueError('Explicit reached group required')
    data=document['inputs']
    def uint(value,bits):
        if type(value) is not int or not 0<=value<1<<bits:raise ValueError(f'Raw uint{bits} required')
        return value
    def vector(value,size):
        if len(value)!=size or any(type(x) not in (int,float) for x in value):
            raise ValueError('Finite numeric vector required')
        result=[f32(x) for x in value]
        if not all(math.isfinite(x) for x in result):raise ValueError('Finite float32 vector required')
        return result
    previous=bytes.fromhex(data['previous_payload_hex'])
    if len(previous)!=288:raise ValueError('Exact 288-byte previous payload required')
    if not 1<=len(data['records'])<=4096:raise ValueError('Authored inspection bound is 1..4096 records')
    width=data['key_width']
    if type(width) is not int or width not in (16,32):raise ValueError('Explicit 16/32-bit group key mode required')
    records=[];keys=[]
    for r in data['records']:
        field00=vector(r['field00'],4)
        first=vector(r['first_point'],3);second=vector(r['second_point'],3)
        identifier=uint(r['row_id'],32);detail=uint(r['detail'],32)
        records.append(struct.pack('<4f3fI3fI',*field00,*first,identifier,*second,detail))
        keys.append(detail&((1<<width)-1))
    if len(set(keys))!=1:raise ValueError('Input must be one reached key group')
    for frame in (data['first_frame'],data['second_frame']):
        if len(frame['basis'])!=3:raise ValueError('Three basis rows required')
        for row in frame['basis']:vector(row,3)
        vector(frame['translation'],3)
    first_index=uint(data['first_index'],16);second_index=uint(data['second_index'],16)
    flag=paired_entry_flag(data['first_entry_flags'],data['second_entry_flags'])
    result=process_pose_link_record_group(previous,records,first_frame=data['first_frame'],
        second_frame=data['second_frame'],first_index=first_index,second_index=second_index,entry_flag=flag)
    payload=result['payload'];rows=[]
    for i,origin in enumerate(result['selected_indices']):
        offset=16+64*i
        rows.append(dict(source_index=origin,
            first_transformed_point=list(struct.unpack_from('<3f',payload,offset+16)),
            second_transformed_point=list(struct.unpack_from('<3f',payload,offset+32)),
            row_id=struct.unpack_from('<I',payload,offset+28)[0],
            cached_word=struct.unpack_from('<I',payload,offset+48)[0],
            pair_indices=list(struct.unpack_from('<HH',payload,offset+56)),
            preserved_tail_hex=payload[offset+60:offset+64].hex()))
    output=dict(schema=document['schema'],provenance=document['provenance'],group_key=keys[0],
        input_count=len(records),active_count=result['count'],selected_indices=result['selected_indices'],
        reduction_applied=result['selection'] is not None,selection=result['selection'],
        resolved_entry_flag=flag,flag_byte=payload[0x114],rows=rows,
        payload_hex=payload.hex(),records_hex=[r.hex() for r in result['records']],
        limits=['One reached key group only; no sorting, cache lookup or payload acquisition',
                'Cached word is raw uint32; no solver meaning or impulse application inferred',
                'Initial bytes and frames supplied; physical units and live identity not established',
                'Fixed-angle scalar trig path validated; other dispatch paths excluded',
                'JSON parsing and input guards are authored; no native failure policy or lifetime guarantee'])
    # Refuse an unserializable numerical result instead of emitting NaN JSON.
    json.dumps(output,allow_nan=False)
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=inspect(json.loads(args.input.read_text()))
    encoded=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(encoded)
    else:print(encoded,end='')


if __name__=='__main__':main()
