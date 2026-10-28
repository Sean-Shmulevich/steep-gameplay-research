"""Offline terrain contacts; LINK_SOLVER.md, Runnable terrain-contact inspection."""
import argparse
import json
import math
from pathlib import Path
import struct
from reference.central_impulse import f32
from .pose_grid_box_contact import emit_grid_box_contacts


def inspect(document):
    if document.get('schema')!='pose-grid-box-v1':raise ValueError('Unsupported schema')
    if document.get('provenance') not in ('authored_synthetic','caller_supplied_observation'):
        raise ValueError('Explicit provenance required')
    data=document['inputs'];grid=data['grid']
    def integer(v,lo,hi):
        if type(v) is not int or not lo<=v<=hi:raise ValueError('Integer outside inspection bounds')
        return v
    def scalar(v):
        if type(v) not in (int,float) or not math.isfinite(f32(v)):raise ValueError('Finite float32 required')
        return f32(v)
    def vector(v,n):
        if not isinstance(v,list) or len(v)!=n:raise ValueError('Wrong vector size')
        return [scalar(x) for x in v]
    width=integer(grid['width'],2,64);height=integer(grid['height'],2,64)
    spacing=vector(grid['spacing'],2);origin=vector(grid['origin'],2)
    if min(spacing)<=0:raise ValueError('Positive spacing required')
    samples=vector(grid['samples'],width*height)
    orientation=integer(grid['orientation'],0,1)
    bounds=vector(grid['z_bounds'],2)
    if bounds[0]>min(samples) or bounds[1]<max(samples):raise ValueError('Z bounds must contain samples')
    frames=[]
    for key in ('terrain_frame','box_frame'):
        if len(data[key])!=4:raise ValueError('Four frame rows required')
        frames.append([vector(row,3) for row in data[key]])
    extents=vector(data['extents'],3)
    if min(extents)<=0:raise ValueError('Positive extents required')
    capacity=integer(data['capacity'],0,128)
    for flag in ('preliminary','edge_enabled','filter_enabled'):
        if type(data[flag]) is not bool:raise ValueError('Boolean flags required')
    profiles=data['profiles']
    for profile in profiles.values():
        for key in ('mask48','mask50'):integer(profile[key],0,2**64-1)
    terrain_profiles=data['terrain_profiles'];box_profile=data['box_profile']
    if terrain_profiles['default20'] not in profiles or box_profile['default20'] not in profiles:
        raise ValueError('Missing default profile')
    mapping=terrain_profiles['mapb0']
    if mapping is not None:
        if len(mapping)!=(width-1)*(height-1):raise ValueError('One map entry per cell required')
        for index in mapping:
            integer(index,0,255)
            if index>=len(terrain_profiles['tablea0']) or terrain_profiles['tablea0'][index] not in profiles:
                raise ValueError('Unresolved mapped profile')
    resource=bytearray(0xc0);resource[0x58]=orientation
    struct.pack_into('<I',resource,0x40,integer(grid['filter_mode'],0,2**32-1))
    struct.pack_into('<2H',resource,0x68,width,height)
    struct.pack_into('<2f',resource,0x70,*spacing)
    struct.pack_into('<3f',resource,0x7c,*origin,bounds[0])
    upper=[f32(f32(f32(n-1)*s)+o) for n,s,o in zip((width,height),spacing,origin)]
    struct.pack_into('<3f',resource,0x88,*upper,bounds[1])
    struct.pack_into('<2H',resource,0x9c,width-1,height-1)
    output=bytearray(capacity*48)
    result=emit_grid_box_contacts(output,capacity,resource,samples,*frames,extents,
        terrain_profiles,box_profile,profiles=profiles,preliminary=data['preliminary'],
        edge_enabled=data['edge_enabled'],filter_enabled=data['filter_enabled'])
    count=min(result,capacity)
    records=[]
    for i in range(count):
        raw=output[i*48:(i+1)*48]
        records.append(dict(normal=list(struct.unpack_from('<3f',raw)),
            separation_field=struct.unpack_from('<f',raw,12)[0],
            first_point=list(struct.unpack_from('<3f',raw,16)),
            second_point=list(struct.unpack_from('<3f',raw,32)),
            triangle_id=struct.unpack_from('<I',raw,44)[0],record_hex=raw.hex()))
    return dict(schema=document['schema'],provenance=document['provenance'],
        return_value=result,retained_record_count=count,
        success_without_record=bool(result and not capacity),records=records,
        output_hex=output.hex(),limits=[
            'Independent offline terrain/box contact generation, not a complete simulation',
            'Separation field may be linear or negative squared; final records do not identify producer kind',
            'Input packing and validation are authored; samples and profiles are caller supplied',
            'Output hex includes inactive storage which may contain discarded contacts'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=json.dumps(inspect(json.loads(args.input.read_text())),indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(result)
    else:print(result,end='')


if __name__=='__main__':main()
