import struct
import unittest
from engine.pose_link_secondary_rows import refresh_pose_secondary_link_rows


def fixture(category=0):
    frame=dict(basis=[[1,0,0],[0,1,0],[0,0,1]],translation=[0,0,0])
    bodies={1:dict(frame=frame,offset128=[0,0,0]),
            2:dict(frame=frame,offset128=[1,0,0],metadata_flags50=0x8000 if category else 0)}
    payload=bytearray(288);struct.pack_into('<3f',payload,0x10,0,0,1)
    struct.pack_into('<3f',payload,0x30,0,0,-2)
    struct.pack_into('<I',payload,0x110,1);payload[0x114]=1
    rows=[bytearray([0xa5]*112),bytearray([0xa5]*128)]
    for row in rows:struct.pack_into('<I',row,4,1)
    context=dict(field18=.5,field1c=.25,counts=[7,8],rows=[[rows[0]],[rows[1]]],
                 result_rows=[bytearray([7]*16),bytearray([8]*16)])
    links={3:dict(flags84=1,first_body=1,second_body=2,payload_count=1,payload_slots=[4])}
    return context,links,bodies,{4:payload}


class SecondaryRowsTests(unittest.TestCase):
    def test_both_categories_response_reset_and_geometry_preservation(self):
        for category in (0,1):
            context,links,bodies,payloads=fixture(category)
            before=bytes(context['rows'][category][0])
            refresh_pose_secondary_link_rows(context,[3],links=links,bodies=bodies,payloads=payloads)
            row=context['rows'][category][0]
            self.assertEqual(struct.unpack_from('<4f',row,0x10),(-1.25,)*4)
            self.assertEqual(context['counts'],[1,0] if category==0 else [0,1])
            self.assertEqual(row[:0x10],before[:0x10])
            self.assertEqual(row[0x20:0x50],before[0x20:0x50])
            self.assertEqual(row[0x58:],before[0x58:])
            self.assertEqual(row[0x50:0x58],bytes(8))
            self.assertEqual(context['result_rows'],[bytes([7]*16),bytes(16)])

    def test_positive_response_clamps_to_positive_zero(self):
        context,links,bodies,payloads=fixture()
        context['field18']=-.5
        refresh_pose_secondary_link_rows(context,[3],links=links,bodies=bodies,payloads=payloads)
        self.assertEqual(context['rows'][0][0][0x10:0x20],bytes(16))

    def test_inactive_links_and_payloads_skip_but_counters_reset(self):
        for target in ('link','payload'):
            context,links,bodies,payloads=fixture()
            if target=='link':links[3]['flags84']=0
            else:payloads[4][0x114]=0
            before=bytes(context['rows'][0][0])
            refresh_pose_secondary_link_rows(context,[3],links=links,bodies=bodies,payloads=payloads)
            self.assertEqual(context['counts'],[0,0])
            self.assertEqual(context['rows'][0][0],before)
            self.assertEqual(context['result_rows'][1],bytes([8]*16))
