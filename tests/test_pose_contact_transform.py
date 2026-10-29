import struct
import unittest
from engine.pose_solver_layout import plan_pose_solver_layout,initialize_pose_solver_storage
from engine.pose_link_arena import correct_pose_contact_transforms
from test_pose_primary_solver import data
from reference.central_impulse import f32


class ContactTransformTests(unittest.TestCase):
    def test_secondary_translation_preserves_original_motion(self):
        counts=[0]*25;counts[0]=1
        plan=plan_pose_solver_layout(counts,1);arena=bytearray(plan['size'])
        initialize_pose_solver_storage(arena,counts,1)
        struct.pack_into('<I',arena,0x38,0x08010000)
        struct.pack_into('<f',arena,0x18,.4)
        struct.pack_into('<4f',arena,plan['rows_offset']+0x20,0,0,-1,-0.)
        view=memoryview(arena);start=plan['body_state_offset'];state=[view[start:start+32]]
        p=bytearray(288);struct.pack_into('<I',p,0x110,1);p[0x114]=1
        struct.pack_into('<3f',p,0x10,0,0,1);struct.pack_into('<3f',p,0x30,0,0,-2)
        body=dict(frame=dict(basis=[[1,0,0],[0,1,0],[0,0,1]],translation=[0,0,0]),offset128=[0,0,0],metadata_flags50=0)
        raw=bytearray(0x200)
        for off,v in ((0x40,[1,0,0]),(0x50,[0,1,0]),(0x60,[0,0,1]),(0x70,[0,0,10]),(0x1a0,[1,2,3])):struct.pack_into('<3f',raw,off,*v)
        saved=bytes(raw[0x1a0:0x1b8])
        ran=correct_pose_contact_transforms(arena,[1],links={1:dict(flags84=1,first_body=10,second_body=10,payload_count=1,payload_slots=[2])},
            bodies={10:body},payloads={2:p},body_data=[data()],body_state=state,body_tokens=[10],raw_bodies={10:raw})
        self.assertTrue(ran)
        self.assertEqual(struct.unpack_from('<f',raw,0x78)[0],f32(10-f32(.8)))
        self.assertEqual(raw[0x1a0:0x1b8],saved)
        self.assertEqual(struct.unpack_from('<3f',raw,0x40),(1,0,0))
