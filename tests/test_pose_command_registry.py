import struct
import unittest
from engine.pose_command_registry import register_pose_constraint,register_pose_constraint_container


class RegistryTests(unittest.TestCase):
    def fixture(self):
        provider=bytearray(0x90);arrays={};events=[]
        for offset in (0x50,0x60,0x70,0x80):
            ptr=offset*100;struct.pack_into('<QII',provider,offset,ptr,0,0);arrays[ptr]=[]
        def grow(p,offset,capacity):
            old,count=struct.unpack_from('<QI',p,offset);new=old+10000
            arrays[new]=arrays[old][:count]+[0]*(capacity-count)
            struct.pack_into('<Q',p,offset,new);struct.pack_into('<I',p,offset+12,capacity)
            events.append((offset,capacity))
        return provider,arrays,grow,events

    def test_single_notification_precedes_kind_and_duplicate_retained(self):
        p,a,g,e=self.fixture();kind=[1];calls=[]
        def notify(token,flag):
            calls.append((token,flag,struct.unpack_from('<I',p,0x68)[0]));kind[0]=4
        for _ in range(2):register_pose_constraint(p,77,arrays=a,grow=g,notify=notify,get_kind=lambda t:kind[0])
        self.assertEqual(calls,[(77,2,1),(77,2,2)])
        self.assertEqual(e,[(0x60,8),(0x70,8)])
        self.assertEqual(a[struct.unpack_from('<Q',p,0x70)[0]][:2],[77,77])

    def test_container_filter_reload_and_captured_count(self):
        p,a,g,e=self.fixture();container=bytearray(0x68)
        struct.pack_into('<QI',container,0x58,100,3);a[100]=[1,2,3];a[200]=[8,9,10]
        visited=[]
        def kind(token):
            visited.append(token)
            if token==1:struct.pack_into('<QI',container,0x58,200,0)
            return 4 if token!=9 else 2
        index=register_pose_constraint_container(p,55,containers={55:container},arrays=a,grow=g,get_kind=kind)
        self.assertEqual(index,0);self.assertEqual(visited,[1,9,10])
        self.assertEqual(a[struct.unpack_from('<Q',p,0x80)[0]][:2],[1,10])
        self.assertEqual(e,[(0x50,8),(0x80,8)])

    def test_empty_container_and_noncommand_constraint(self):
        p,a,g,e=self.fixture()
        register_pose_constraint(p,77,arrays=a,grow=g,notify=lambda *x:None,get_kind=lambda t:3)
        index=register_pose_constraint_container(p,55,containers={55:bytearray(0x68)},arrays=a,grow=g,get_kind=lambda t:self.fail('no children'))
        self.assertEqual(index,0);self.assertEqual(e,[(0x60,8),(0x50,8)])
        self.assertEqual(struct.unpack_from('<I',p,0x78)[0],0)
        self.assertEqual(struct.unpack_from('<I',p,0x88)[0],0)

    def test_registered_lists_feed_preparation(self):
        from engine.pose_command_prepare import prepare_retained_pose_commands
        p,a,g,e=self.fixture();r=bytearray(0x200);body=bytearray(0x40)
        struct.pack_into('<Q',r,8,1);struct.pack_into('<Q',r,0x1f8,7)
        struct.pack_into('<Q',body,0x30,2)
        owner=bytearray(0x50);struct.pack_into('<Q',owner,0x20,20)
        container=bytearray(0x68);struct.pack_into('<QI',container,0x58,300,2);a[300]=[77,88]
        kind=lambda t:4 if t==77 else 2
        register_pose_constraint(p,77,arrays=a,grow=g,notify=lambda *x:None,get_kind=kind)
        register_pose_constraint_container(p,55,containers={55:container},arrays=a,grow=g,get_kind=kind)
        calls=[]
        def invoke(fn,first,second,commands,count,scalar,mode,user):
            calls.append((fn,first,second,scalar,mode));struct.pack_into('<I',count,0,1)
        prepare_retained_pose_commands(9,scalar=.25,owners={9:owner},providers={20:p},arrays=a,
            constraints={77:r},bodies={1:body},metadata={2:bytearray(0x60)},invoke=invoke)
        self.assertEqual(calls,[(7,1,0,4.,1)]*2)

    def test_individual_removal_order_and_first_match(self):
        from engine.pose_command_registry import unregister_pose_constraint
        p,a,g,e=self.fixture()
        for token in (77,88,77):
            register_pose_constraint(p,token,arrays=a,grow=g,notify=lambda *x:None,get_kind=lambda t:4)
        events=[]
        def detach(token,selector):
            events.append((token,selector,struct.unpack_from('<I',p,0x78)[0],
                           struct.unpack_from('<I',p,0x68)[0]))
        unregister_pose_constraint(p,77,arrays=a,get_kind=lambda t:4,detach=detach)
        self.assertEqual(events,[(77,2,2,3)])
        self.assertEqual(a[struct.unpack_from('<Q',p,0x60)[0]][:3],[77,88,77])
        self.assertEqual(struct.unpack_from('<I',p,0x68)[0],2)

    def test_missing_membership_guard_and_noncommand_removal(self):
        from engine.pose_command_registry import unregister_pose_constraint
        p,a,g,e=self.fixture();before=bytes(p)
        with self.assertRaises(ValueError):
            unregister_pose_constraint(p,77,arrays=a,get_kind=lambda t:4,detach=lambda *x:self.fail('detach'))
        self.assertEqual(bytes(p),before)
        register_pose_constraint(p,77,arrays=a,grow=g,notify=lambda *x:None,get_kind=lambda t:2)
        calls=[]
        unregister_pose_constraint(p,77,arrays=a,get_kind=lambda t:2,detach=lambda *x:calls.append(x))
        self.assertEqual(calls,[(77,2)]);self.assertEqual(struct.unpack_from('<I',p,0x68)[0],0)

    def test_doubling_and_captured_container_return(self):
        p,a,g,e=self.fixture();struct.pack_into('<II',p,0x58,1,1)
        old=struct.unpack_from('<Q',p,0x50)[0];a[old]=[33]
        index=register_pose_constraint_container(p,55,containers={55:bytearray(0x68)},arrays=a,grow=g,get_kind=lambda t:4)
        self.assertEqual(index,1);self.assertEqual(e,[(0x50,2)])
        self.assertEqual(a[struct.unpack_from('<Q',p,0x50)[0]],[33,55])


if __name__=='__main__':unittest.main()
