import struct
import unittest
from engine.pose_link_feedback import write_pose_link_feedback
from engine.pose_link_pipeline import process_pose_link_record_group


class FeedbackTests(unittest.TestCase):
    def fixture(self):
        p=bytearray([0xa5])*288;p[0x114]=1;struct.pack_into('<I',p,0x110,2)
        struct.pack_into('<I',p,0x44,1);struct.pack_into('<I',p,0x84,0)
        return p,{1:dict(flags84=1,payload_count=1,payload_slots=[2])}

    def test_raw_result_lane_and_retained_padding(self):
        p,links=self.fixture();before=p[:]
        results=[bytes.fromhex('0000807f')+bytes(12),bytes.fromhex('0100c07f')+bytes(12)]
        write_pose_link_feedback(dict(flags38=1<<29,result_rows=results),[1],links=links,payloads={2:p})
        before[0x40:0x44]=results[1][:4];before[0x80:0x84]=results[0][:4]
        self.assertEqual(p,before)

    def test_disabled_feedback_zeroes_without_reading_results(self):
        p,links=self.fixture()
        write_pose_link_feedback(dict(flags38=0,result_rows=[]),[1],links=links,payloads={2:p})
        self.assertEqual(p[0x40:0x44]+p[0x80:0x84],bytes(8))

    def test_both_enable_gates_preserve_cached_words(self):
        for gate in ('link','payload'):
            p,links=self.fixture()
            if gate=='link':links[1]['flags84']=0
            else:p[0x114]=0
            before=p[:]
            write_pose_link_feedback(dict(flags38=0,result_rows=[]),[1],links=links,payloads={2:p})
            self.assertEqual(p,before)

    def test_feedback_survives_next_matching_geometry_update(self):
        p,links=self.fixture();struct.pack_into('<I',p,0x2c,7)
        results=[struct.pack('<4I',123,0,0,0),struct.pack('<4I',456,0,0,0)]
        write_pose_link_feedback(dict(flags38=1<<29,result_rows=results),[1],links=links,payloads={2:p})
        record=bytearray(48);struct.pack_into('<I',record,28,7)
        frame=dict(basis=[[1,0,0],[0,1,0],[0,0,1]],translation=[0,0,0])
        result=process_pose_link_record_group(p,[record],first_frame=frame,second_frame=frame,
            first_index=0,second_index=1,entry_flag=True)
        self.assertEqual(struct.unpack_from('<I',result['payload'],0x40)[0],456)
        # New builder index is reset; a later builder must assign the next result slot.
        self.assertEqual(struct.unpack_from('<I',result['payload'],0x44)[0],0)
