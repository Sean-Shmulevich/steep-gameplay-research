"""Offline contact inspection; LINK_SOLVER.md, Runnable box-triangle inspection."""
import argparse
import json
import math
from pathlib import Path
import struct
from reference.central_impulse import f32
from .pose_box_triangle_contact import emit_box_triangle_contacts
from .pose_contact_shapes import box_contact_shape, triangle_contact_shape
from .pose_contact_axis_selection import select_geometry_contact_axis


def inspect(document):
    if document.get('schema') != 'pose-box-triangle-v1':
        raise ValueError('Unsupported schema')
    if document.get('provenance') not in ('authored_synthetic', 'caller_supplied_observation'):
        raise ValueError('Explicit provenance required')
    data = document['inputs']
    def vector(v):
        if len(v) != 3 or any(type(x) not in (int,float) or not math.isfinite(f32(x)) for x in v):
            raise ValueError('Three finite float32 components required')
    vector(data['extents'])
    if any(x <= 0 for x in data['extents']):
        raise ValueError('Positive extents required')
    frame, triangle = data['box_frame'], data['triangle']
    if len(frame) != 4 or len(triangle) != 3:
        raise ValueError('Four frame rows and three triangle vertices required')
    for row in frame+triangle:vector(row)
    capacity = data['capacity']
    if type(capacity) is not int or not 0 <= capacity <= 128:
        raise ValueError('Capacity within0..128 required')
    for flag in ('reduce_to_four','edge_enabled'):
        if type(data[flag]) is not bool:raise ValueError('Boolean flags required')
    output = bytearray(capacity*48)
    count = emit_box_triangle_contacts(output,capacity,data['extents'],frame,triangle,
                                       data['reduce_to_four'],data['edge_enabled'])
    selection = select_geometry_contact_axis(frame,box_contact_shape(data['extents']),
        [[1,0,0],[0,1,0],[0,0,1],[0,0,0]],triangle_contact_shape(*triangle),
        edge_enabled=data['edge_enabled'])
    records=[]
    for i in range(count):
        raw=output[i*48:(i+1)*48]
        records.append(dict(normal=list(struct.unpack_from('<3f',raw)),
            separation=struct.unpack_from('<f',raw,12)[0],
            separation_kind='negative_squared' if selection['kind']==2 else 'linear_plane',
            first_point=list(struct.unpack_from('<3f',raw,16)),
            second_point=list(struct.unpack_from('<3f',raw,32)),record_hex=raw.hex()))
    return dict(schema=document['schema'],provenance=document['provenance'],
        selection=selection,count=count,records=records,
        limits=['Independent offline local producer, not live game or full terrain collision',
                'Input validation and capacity bound are authored',
                'Finite nondegenerate helper domains; fixed-angle scalar trig specialization'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    text=json.dumps(inspect(json.loads(args.input.read_text())),indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(text)
    else:print(text,end='')


if __name__ == '__main__':main()
