import random
import struct
import unittest
from engine.pose_body_tree import remove_pose_tree_body
from engine.pose_command_registry import unregister_pose_constraint_container


def integer(raw,offset):return struct.unpack_from('<i',raw,offset)[0]


class BodyTreeTests(unittest.TestCase):
    def fixture(self,levels=3):
        n=2**levels-1;self.nodes=bytearray(n*32);self.d=bytearray(32);self.b=bytearray(0xa0);self.m=bytearray(0x60)
        self.destroyed=[];struct.pack_into('<Q',self.b,0x30,2)
        def build(lo,hi,parent=-1):
            if lo>=hi:return -1
            mid=(lo+hi)//2
            left=build(lo,mid,mid);right=build(mid+1,hi,mid)
            struct.pack_into('<iii',self.nodes,mid*32,left,right,parent)
            struct.pack_into('<QI',self.nodes,mid*32+16,100+mid,0x80000000+mid)
            return mid
        root=build(0,n);struct.pack_into('<Qii',self.d,0,3,n,0);struct.pack_into('<ii',self.d,20,root,-1)
        self.kw=dict(bodies={1:self.b},metadata={2:self.m},node_arrays={3:self.nodes},destroy=lambda t,f:self.destroyed.append((t,f)))

    def remove(self,index):
        struct.pack_into('<I',self.m,0x54,0x80000000+index)
        remove_pose_tree_body(self.d,1,**self.kw)

    def check_invariants(self):
        seen=set()
        def walk(i,parent=-1,low=-1,high=0x100000000):
            if i==-1:return 1
            self.assertNotIn(i,seen);seen.add(i);o=i*32
            left,right,p=struct.unpack_from('<iii',self.nodes,o);key=struct.unpack_from('<I',self.nodes,o+24)[0]
            self.assertEqual(p,parent);self.assertTrue(low<key<high);self.assertEqual(self.nodes[o+13],0)
            if self.nodes[o+12]:
                for child in (left,right):
                    if child!=-1:self.assertEqual(self.nodes[child*32+12],0)
            a=walk(left,i,low,key);b=walk(right,i,key,high);self.assertEqual(a,b)
            return a+(self.nodes[o+12]==0)
        root=integer(self.d,20)
        if root!=-1:self.assertEqual(self.nodes[root*32+12],0)
        walk(root);self.assertEqual(len(seen),integer(self.d,8))
        frees=set();i=integer(self.d,24);prev=-1
        while i!=-1:
            self.assertNotIn(i,seen|frees);frees.add(i);self.assertEqual(integer(self.nodes,i*32),prev)
            self.assertEqual(self.nodes[i*32+13],1);prev,i=i,integer(self.nodes,i*32+4)
        self.assertEqual(len(frees),integer(self.d,12))
        self.assertEqual(seen|frees,set(range(integer(self.d,8)+integer(self.d,12))))

    def test_random_removal_preserves_tree_and_slot_invariants(self):
        for seed in range(12):
            self.fixture(5);order=list(range(31));random.Random(seed).shuffle(order)
            for i in order:self.remove(i);self.check_invariants()
            self.assertEqual(self.destroyed,[(100+i,1) for i in order])

    def test_two_child_removal_destroys_original_value(self):
        self.fixture();self.remove(3)
        self.assertEqual(self.destroyed,[(103,1)])
        self.assertEqual(struct.unpack_from('<Q',self.nodes,3*32+16)[0],102)
        self.assertEqual(integer(self.d,24),2);self.check_invariants()

    def test_missing_key_and_null_value(self):
        self.fixture(1);before=bytes(self.d)+bytes(self.nodes);self.remove(7)
        self.assertEqual(bytes(self.d)+bytes(self.nodes),before);self.assertEqual(self.destroyed,[])
        struct.pack_into('<Q',self.nodes,16,0);self.remove(0);self.remove(0)
        self.assertEqual(self.destroyed,[]);self.check_invariants()

    def test_container_tree_service_uses_real_removal(self):
        self.fixture(1);provider=bytearray(0xf0);provider[0xd0:0xf0]=self.d
        struct.pack_into('<QII',provider,0x50,10,1,1);container=bytearray(0x68)
        struct.pack_into('<QI',container,0x38,11,1);self.m[0x52]=8
        struct.pack_into('<I',self.m,0x54,0x80000000)
        calls=[]
        def tree(t,b):
            self.assertEqual(t,1000+0xd0)
            remove_pose_tree_body(memoryview(provider)[0xd0:0xf0],b,**self.kw)
        def body(p,b,o):
            self.assertEqual(integer(provider,0xd8),0);calls.append(b)
        unregister_pose_constraint_container(provider,7,bytearray(16),provider_token=1000,
            containers={7:container},constraints={},bodies={1:self.b},metadata={2:self.m},
            arrays={10:[7],11:[1]},get_kind=lambda t:self.fail('no children'),
            remove_tree_body=tree,process_body=body,grow_output=lambda *a:self.fail('no output'))
        self.assertEqual(calls,[1]);self.assertEqual(self.destroyed,[(100,1)])
        self.assertEqual(integer(provider,0x58),0)


if __name__=='__main__':unittest.main()
