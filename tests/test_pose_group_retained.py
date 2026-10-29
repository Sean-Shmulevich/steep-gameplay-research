import struct
import unittest
from tests.test_pose_group_runtime import fixture
from tests.test_pose_poststep_runtime import bind
from engine.pose_group_retained import read_retained_pose_group,run_retained_pose_group_pass
from engine.pose_link_payloads import clear_pose_link_contacts


def view(args,links=None,entry_arrays=None):
    return read_retained_pose_group(args['groups'][99],arrays=args['arrays'],
        bodies=args['bodies'],metadata=args['metadata'],links=links or {},
        entry_arrays=entry_arrays or {},constraints=args['constraints'],get_kind=args['get_kind'])


class RetainedGroupTests(unittest.TestCase):
    def test_current_frames_and_motion_are_reread(self):
        _,_,args,_=fixture()
        before=view(args)
        struct.pack_into('<3f',args['bodies'][1],0x70,4,5,6)
        struct.pack_into('<3f',args['bodies'][1],0x1a0,7,8,9)
        after=view(args)
        self.assertEqual(before['bodies'][1]['frame']['translation'],[0,0,0])
        self.assertEqual(after['bodies'][1]['frame']['translation'],[4,5,6])
        self.assertEqual(after['bodies'][1]['motion1a0'],[7,8,9])

    def test_retired_count_excludes_stale_array_entries(self):
        _,_,args,_=fixture()
        struct.pack_into('<QI',args['groups'][99],0x40,200,1);args['arrays'][200]=[4]
        link=bytearray(0x90);struct.pack_into('<2Q',link,8,1,2)
        struct.pack_into('<QI',link,0x58,500,1);link[0x84]=1
        entries=bytearray(struct.pack('<QQ',99,600));calls=[]
        self.assertEqual(view(args,{4:link},{500:entries})['links'][4]['payload_slots'],[600])
        clear_pose_link_contacts(link,entry_arrays={500:entries},release=calls.append)
        after=view(args,{4:link},{})
        self.assertEqual(after['links'][4]['payload_slots'],[])
        self.assertEqual(after['links'][4]['payload_count'],0)
        self.assertEqual(struct.unpack_from('<Q',entries,8)[0],600)
        self.assertEqual(calls,[600])

    def test_resource_count_and_entry_stride(self):
        _,_,args,_=fixture();body=args['bodies'][1]
        struct.pack_into('<QH',body,0xb8,500,2)
        entries=bytearray(144)
        struct.pack_into('<Q',entries,16,10);struct.pack_into('<Q',entries,88,20)
        self.assertEqual(view(args,entry_arrays={500:entries})['bodies'][1]['entries'],[10,20])
        struct.pack_into('<H',body,0xc0,1)
        self.assertEqual(view(args,entry_arrays={500:entries})['bodies'][1]['entries'],[10])

    def test_repeated_pass_reuses_mutated_records(self):
        arena,_,args,_=fixture();poststep=bind(args)
        settings=bytearray(64);struct.pack_into('<H',settings,0x28,2)
        positions=[]
        for _ in range(4):
            plan=run_retained_pose_group_pass(arena,settings,scalar=.5,group_token=99,
                base_token=0,groups=args['groups'],arrays=args['arrays'],bodies=args['bodies'],
                metadata=args['metadata'],links={},entry_arrays={},constraints=args['constraints'],
                get_kind=args['get_kind'],payloads={},resources={},profiles={},modes={},
                poststep=poststep,atan2=args['atan2'])
            positions.append(struct.unpack_from('<f',args['bodies'][1],0x70)[0])
            self.assertEqual(plan['row_counts'][10],1)
        self.assertEqual(len(set(positions)),4)
