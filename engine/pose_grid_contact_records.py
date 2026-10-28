"""Terrain caller record conversion; LINK_SOLVER.md, Terrain record roles."""
import struct


def convert_grid_contact_records(records, start, count, triangle_id):
    """Reverse point roles/normal bits and identify each record's terrain triangle.

    Scalar separation and field0x1c are retained, including arbitrary bit patterns.
    Buffer/count/id validation is authored; native caller supplies valid storage.
    """
    if start < 0 or count < 0 or (start+count)*48 > len(records):
        raise ValueError('Complete retained record range required')
    if not 0 <= triangle_id < 2**32:
        raise ValueError('uint32 triangle identifier required')
    for i in range(start,start+count):
        offset = i*48
        first = bytes(records[offset+16:offset+28])
        records[offset+16:offset+28] = records[offset+32:offset+44]
        records[offset+32:offset+44] = first
        for j in range(3):
            value = struct.unpack_from('<I',records,offset+j*4)[0]
            struct.pack_into('<I',records,offset+j*4,value ^ 0x80000000)
        struct.pack_into('<I',records,offset+44,triangle_id)
